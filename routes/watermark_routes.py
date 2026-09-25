"""Embed, result, detect, download and safe file serving."""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, abort, current_app, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

from watermark.errors import WatermarkError
from watermark.service import Storage, detect_bytes, embed_upload, load_job
from watermark.utils import allowed_file, is_valid_job_id, read_image

wm_bp = Blueprint("wm", __name__)

_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}


def storage() -> Storage:
    return current_app.config["STORAGE"]


def _read_upload(field: str = "image"):
    """Return (bytes, safe display name) of an uploaded image or raise WatermarkError."""
    file = request.files.get(field)
    if file is None or not file.filename:
        raise WatermarkError("Pilih file gambar terlebih dahulu.")
    if not allowed_file(file.filename):
        raise WatermarkError("Format file tidak didukung. Gunakan PNG, JPG, atau JPEG.")
    return file.read(), secure_filename(file.filename) or "image"


@wm_bp.route("/embed", methods=["GET", "POST"])
def embed():
    if request.method == "GET":
        return render_template("embed.html", form={"method": "dct"})
    form = {"watermark_text": request.form.get("watermark_text", ""), "method": request.form.get("method", "dct")}
    try:
        data, name = _read_upload()
        meta = embed_upload(data, name, form["watermark_text"], request.form.get("secret_key", ""), form["method"], storage())
    except WatermarkError as exc:
        return render_template("embed.html", form=form, error=str(exc)), 400
    return redirect(url_for("wm.result", job_id=meta["job_id"]))  # PRG: refresh tidak mengulang embedding


@wm_bp.route("/result/<job_id>")
def result(job_id: str):
    job = load_job(job_id, storage())
    if job is None:
        abort(404)
    return render_template("result.html", job=job)


@wm_bp.route("/download/<job_id>")
def download(job_id: str):
    if load_job(job_id, storage()) is None:
        abort(404)
    return send_from_directory(storage().watermarked, f"{job_id}.png", as_attachment=True,
                               download_name=f"watermarked_{job_id}.png")


@wm_bp.route("/detect", methods=["GET", "POST"])
def detect():
    job_id = request.values.get("job", "")
    job = load_job(job_id, storage()) if job_id else None
    form = {"method": (job or {}).get("method_key", request.form.get("method", "dct")),
            "expected": request.form.get("expected", (job or {}).get("watermark_text", "")),
            "job": job["job_id"] if job else ""}
    if request.method == "GET":
        return render_template("detect.html", form=form, job=job)
    try:
        if request.files.get("image") and request.files["image"].filename:
            data, _ = _read_upload()
        elif job:
            data = (storage().watermarked / f"{job['job_id']}.png").read_bytes()
        else:
            raise WatermarkError("Pilih file gambar terlebih dahulu.")
        size = None
        width, height = request.form.get("orig_w", "").strip(), request.form.get("orig_h", "").strip()
        if width or height:
            if not (width.isdigit() and height.isdigit() and 16 <= int(width) <= 8000 and 16 <= int(height) <= 8000):
                raise WatermarkError("Ukuran asli harus berupa angka piksel (lebar dan tinggi).")
            size = (int(width), int(height))
        result_data = detect_bytes(data, request.form.get("secret_key", ""), form["method"],
                                   request.form.get("expected", ""), size)
    except WatermarkError as exc:
        return render_template("detect.html", form=form, job=job, error=str(exc)), 400
    return render_template("detect.html", form=form, job=job, detection=result_data)


@wm_bp.route("/files/<category>/<path:filename>")
def files(category: str, filename: str):
    """Serve generated images. Category is whitelisted; send_from_directory blocks path traversal."""
    folders = {"original": storage().upload, "watermarked": storage().watermarked,
               "attacks": storage().attacks, "charts": storage().charts}
    folder = folders.get(category)
    if folder is None or Path(filename).suffix.lower() not in _IMAGE_SUFFIXES:
        abort(404)
    return send_from_directory(folder, filename)
