"""Attack testing, method comparison and report download."""

from __future__ import annotations

import re

from flask import Blueprint, abort, current_app, redirect, render_template, request, send_from_directory, url_for

from watermark import config
from watermark.errors import WatermarkError
from watermark.evaluation import (
    evaluate_dataset,
    generate_synthetic_dataset,
    list_dataset_images,
    load_results_json,
    save_results_json,
)
from watermark.report import comparison_facts, make_charts, summarize, write_xlsx
from watermark.service import embed_upload, load_job, load_run, run_attack_test, validate_inputs
from watermark.utils import is_valid_job_id
from routes.watermark_routes import _read_upload, storage

testing_bp = Blueprint("testing", __name__)

_REPORT_RE = re.compile(r"^(run_[0-9a-f]{12}\.xlsx|" + re.escape(config.REPORT_XLSX_NAME) + ")$")


@testing_bp.route("/testing", methods=["GET", "POST"])
def attack_testing():
    job_id = request.values.get("job", "")
    job = load_job(job_id, storage()) if job_id else None
    form = {"watermark_text": request.form.get("watermark_text", (job or {}).get("watermark_text", "")),
            "method": (job or {}).get("method_key", request.form.get("method", "dct"))}
    if request.method == "GET":
        return render_template("testing.html", form=form, job=job)
    try:
        secret_key = request.form.get("secret_key", "")
        if job is None:  # tidak ada job sebelumnya -> upload baru, embed dulu
            data, name = _read_upload()
            job = embed_upload(data, name, form["watermark_text"], secret_key, form["method"], storage())
        else:
            validate_inputs(job["watermark_text"], secret_key, job["method_key"])
        run = run_attack_test(job, secret_key, storage())
    except WatermarkError as exc:
        return render_template("testing.html", form=form, job=job, error=str(exc)), 400
    return redirect(url_for("testing.run_result", run_id=run["run_id"]))


@testing_bp.route("/testing/run/<run_id>")
def run_result(run_id: str):
    run = load_run(run_id, storage())
    if run is None:
        abort(404)
    job = load_job(run["job_id"], storage())
    return render_template("testing_result.html", run=run, job=job, summary=summarize(run["rows"]))


@testing_bp.route("/comparison")
def comparison():
    results = load_results_json(storage().reports / config.LAST_EVALUATION_JSON)
    context = {"results": None, "dataset_count": len(list_dataset_images(current_app.config["DATASET_DIR"]))}
    if results:
        summary = summarize(results["rows"])
        pivot = {}
        for item in summary:
            entry = pivot.setdefault(item["attack_key"], {"short": item["short"], "attack": item["attack"], "parameter": item["parameter"]})
            entry[item["method_key"]] = item
        context.update(results=results, pivot=list(pivot.values()), facts=comparison_facts(results["rows"]),
                       xlsx_ready=(storage().reports / config.REPORT_XLSX_NAME).exists())
    return render_template("comparison.html", **context)


@testing_bp.route("/comparison/run", methods=["POST"])
def run_comparison():
    text = request.form.get("watermark_text", "").strip() or config.DEFAULT_WATERMARK_TEXT
    secret_key = request.form.get("secret_key", "")
    dataset_dir = current_app.config["DATASET_DIR"]
    try:
        validate_inputs(text, secret_key, "dct")
        if not list_dataset_images(dataset_dir):
            generate_synthetic_dataset(dataset_dir)
        results = evaluate_dataset(dataset_dir, secret_key, text,
                                   watermarked_dir=storage().watermarked / "dataset",
                                   attack_dir=storage().attacks / "dataset")
    except WatermarkError as exc:
        return render_template("comparison.html", results=None, error=str(exc),
                               dataset_count=len(list_dataset_images(dataset_dir))), 400
    save_results_json(results, storage().reports / config.LAST_EVALUATION_JSON)
    write_xlsx(results, storage().reports / config.REPORT_XLSX_NAME)
    make_charts(results["rows"], storage().charts)
    return redirect(url_for("testing.comparison"))


@testing_bp.route("/report/<name>")
def download_report(name: str):
    if not _REPORT_RE.match(name):
        abort(404)
    if name.startswith("run_") and not is_valid_job_id(name[4:16]):
        abort(404)
    if not (storage().reports / name).exists():
        abort(404)
    return send_from_directory(storage().reports, name, as_attachment=True)
