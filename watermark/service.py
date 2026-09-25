"""Watermark service: the workflow used by the Flask routes.

Browser -> Flask route -> service (validasi + embed/detect) -> DCT/LSB -> metrics.
Secret key hanya hidup di memori selama request; tidak disimpan dan tidak di-log.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import cv2
import numpy as np

from . import config
from .errors import ImageValidationError, WatermarkError
from .methods import get_method
from .metrics import calculate_ber, calculate_nc, calculate_psnr
from .payload import encode_payload
from .utils import (
    check_image,
    cleanup_old_files,
    decode_image,
    is_valid_job_id,
    limit_image_size,
    new_job_id,
    read_image,
    save_png,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Storage:
    """Folders used by the web app (injectable so tests can use temp folders)."""

    upload: Path
    watermarked: Path
    attacks: Path
    extracted: Path
    charts: Path
    reports: Path

    @classmethod
    def default(cls) -> "Storage":
        return cls(config.UPLOAD_DIR, config.WATERMARKED_DIR, config.ATTACK_DIR,
                   config.EXTRACTED_DIR, config.CHART_DIR, config.REPORT_DIR)

    def ensure(self) -> None:
        for folder in (self.upload, self.watermarked, self.attacks, self.extracted, self.charts, self.reports):
            folder.mkdir(parents=True, exist_ok=True)

    def cleanup(self) -> None:
        """Remove temporary files older than TEMP_FILE_MAX_AGE_HOURS."""
        for folder in (self.upload, self.watermarked, self.extracted, self.attacks):
            cleanup_old_files(folder)
        cleanup_old_files(self.charts, pattern="run_*")
        cleanup_old_files(self.reports, pattern="run_*")


def validate_inputs(text: str, secret_key: str, method_key: str) -> Tuple[str, str]:
    """Return (clean_text, method_key) or raise WatermarkError with a clear message."""
    text = (text or "").strip()
    if not text:
        raise WatermarkError("Teks watermark tidak boleh kosong.")
    if not secret_key:
        raise WatermarkError("Secret key tidak boleh kosong.")
    get_method(method_key)
    encode_payload(text)  # cek panjang maksimum
    return text, method_key


def embed_upload(data: bytes, display_name: str, text: str, secret_key: str, method_key: str, storage: Storage) -> Dict:
    """Validate, embed, verify extraction from the saved file and store job metadata."""
    text, method_key = validate_inputs(text, secret_key, method_key)
    method = get_method(method_key)
    logger.info("Image uploaded (%d bytes)", len(data))
    image, resized, (orig_w, orig_h) = limit_image_size(decode_image(data))
    check_image(image)
    storage.ensure()
    storage.cleanup()

    embedded = method.embed(image, text, secret_key)
    job_id = new_job_id()
    save_png(storage.upload / f"{job_id}.png", image)
    save_png(storage.watermarked / f"{job_id}.png", embedded.image)

    watermarked_file = read_image(storage.watermarked / f"{job_id}.png")  # verifikasi dari file
    extraction = method.extract(watermarked_file, secret_key, force_length=encode_payload(text).data_length)
    payload = encode_payload(text)
    psnr = calculate_psnr(image, watermarked_file)
    meta = {
        "job_id": job_id,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "filename": display_name,
        "method_key": method.key,
        "method": method.label,
        "watermark_text": text,
        "width": image.shape[1],
        "height": image.shape[0],
        "original_width": orig_w,
        "original_height": orig_h,
        "was_resized": resized,
        "psnr": psnr if np.isfinite(psnr) else None,
        "psnr_is_infinite": not np.isfinite(psnr),
        "nc": calculate_nc(payload.all_bits, extraction.raw_bits),
        "ber": calculate_ber(payload.all_bits, extraction.raw_bits),
        "extracted": extraction.watermark,
        "valid": extraction.valid,
        "message": extraction.message,
        "warning": "Watermark strength terlalu tinggi. Kualitas citra menurun." if psnr < config.PSNR_WARNING_DB else "",
        "info": embedded.info,
    }
    (storage.extracted / f"{job_id}.txt").write_text(extraction.watermark, encoding="utf-8")
    (storage.watermarked / f"{job_id}.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Embedding job %s stored (method=%s)", job_id, method.key)
    return meta


def load_job(job_id: str, storage: Storage) -> Optional[Dict]:
    """Load stored job metadata; None if the id is malformed or unknown."""
    if not is_valid_job_id(job_id):
        return None
    path = storage.watermarked / f"{job_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def detect_bytes(
    data: bytes,
    secret_key: str,
    method_key: str,
    expected_text: str = "",
    original_size: Optional[Tuple[int, int]] = None,
) -> Dict:
    """Detect a watermark in an uploaded (possibly attacked) image.

    ``expected_text`` (opsional) dipakai menghitung NC/BER. ``original_size``
    (opsional) dipakai untuk mengembalikan citra hasil resize ke ukuran asli.
    """
    if not secret_key:
        raise WatermarkError("Secret key tidak boleh kosong.")
    method = get_method(method_key)
    image = decode_image(data)
    note = ""
    if original_size and original_size != (image.shape[1], image.shape[0]):
        image = cv2.resize(image, original_size, interpolation=cv2.INTER_CUBIC)
        note = f"Citra diskalakan kembali ke {original_size[0]}x{original_size[1]} sebelum deteksi."
    check_image(image)

    expected = expected_text.strip()
    payload = encode_payload(expected) if expected else None
    extraction = method.extract(image, secret_key, force_length=payload.data_length if payload else None)
    result = {
        "method": method.label,
        "valid": extraction.valid,
        "watermark": extraction.watermark,
        "message": extraction.message,
        "nc": None,
        "ber": None,
        "note": note,
    }
    status_ok = extraction.valid
    if payload is not None:
        result["nc"] = calculate_nc(payload.all_bits, extraction.raw_bits)
        result["ber"] = calculate_ber(payload.all_bits, extraction.raw_bits)
        if extraction.valid and extraction.watermark != expected:
            status_ok = False
            result["message"] = "Watermark terbaca tetapi berbeda dari teks yang diharapkan."
    if not extraction.valid and not result["message"]:
        result["message"] = "Watermark tidak valid atau secret key salah."
    result["status"] = "SUCCESS" if status_ok else "FAIL"
    logger.info("Detection finished: %s", result["status"])
    return result


# ------------------------------------------------------------ attack testing
def run_attack_test(job: Dict, secret_key: str, storage: Storage) -> Dict:
    """Run all attacks for one stored job and persist tables, charts and XLSX."""
    from .attack_engine import run_all_attacks
    from .attacks import build_attack_specs
    from .evaluation import save_results_json
    from .report import make_charts, write_xlsx

    if not secret_key:
        raise WatermarkError("Secret key tidak boleh kosong.")
    job_id = job["job_id"]
    original = read_image(storage.upload / f"{job_id}.png")
    watermarked = read_image(storage.watermarked / f"{job_id}.png")
    run_id = new_job_id()
    logger.info("Attack testing run %s started (method=%s)", run_id, job["method_key"])
    rows = run_all_attacks(
        original, watermarked, job["method_key"], secret_key, job["watermark_text"],
        storage.attacks / run_id, image_name="image",
    )
    results = {
        "run_id": run_id,
        "job_id": job_id,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "watermark_text": job["watermark_text"],
        "methods": [job["method"]],
        "method_key": job["method_key"],
        "filename": job.get("filename", ""),
        "rows": rows,
        "dataset": [{"image": "image", "file": job.get("filename", ""), "width": job["width"], "height": job["height"],
                     "size_kb": round((storage.upload / f"{job_id}.png").stat().st_size / 1024, 1),
                     "sha256": rows[0]["file_sha256"][:12], "note": "citra yang diunggah"}],
        "attacks": [{"key": s.key, "name": s.name, "parameter": s.parameter, "short": s.short} for s in build_attack_specs()],
        "config": {"embed_strength": config.EMBED_STRENGTH},
        "key_accepted": rows[0]["status"] == "SUCCESS",
    }
    results["charts"] = make_charts(rows, storage.charts, prefix=f"run_{run_id}_")
    write_xlsx(results, storage.reports / f"run_{run_id}.xlsx")
    save_results_json(results, storage.reports / f"run_{run_id}.json")
    return results


def load_run(run_id: str, storage: Storage) -> Optional[Dict]:
    """Load the stored results of one attack-testing run."""
    from .evaluation import load_results_json

    if not is_valid_job_id(run_id):
        return None
    return load_results_json(storage.reports / f"run_{run_id}.json")
