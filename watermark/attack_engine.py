"""Attack testing engine: run every attack, extract again, compute metrics."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional

import numpy as np

from .attacks import AttackSpec, build_attack_specs, restore_geometry, save_attack_image
from .errors import WatermarkError
from .methods import get_method
from .metrics import calculate_ber, calculate_nc, calculate_psnr
from .payload import encode_payload
from .utils import file_sha256, read_image

logger = logging.getLogger(__name__)


def _psnr_after_attack(original: np.ndarray, attacked: np.ndarray, restored: np.ndarray, geometry: Optional[dict]) -> float:
    """PSNR between the ORIGINAL (cover) image and the attacked image.

    * crop   : bandingkan dengan potongan area yang sama dari citra asli
    * resize : bandingkan hasil resize yang sudah dikembalikan ke ukuran asli
    * lainnya: bandingkan langsung
    """
    if geometry and geometry["type"] == "crop":
        x0, y0 = geometry["x0"], geometry["y0"]
        h, w = attacked.shape[:2]
        return calculate_psnr(original[y0:y0 + h, x0:x0 + w], attacked)
    if geometry and geometry["type"] == "resize":
        return calculate_psnr(original, restored)
    return calculate_psnr(original, attacked)


def run_single_attack(
    spec: AttackSpec,
    original: np.ndarray,
    watermarked: np.ndarray,
    method_key: str,
    secret_key: str,
    watermark_text: str,
    out_path: Path,
) -> Dict:
    """Apply one attack, save it as a file, re-read the file and extract."""
    method = get_method(method_key)
    payload = encode_payload(watermark_text)

    started = time.perf_counter()
    output = spec.apply(watermarked)
    save_attack_image(spec, output.image, out_path)
    attacked = read_image(out_path)  # metrik dihitung dari FILE hasil serangan
    restored, region = restore_geometry(attacked, output.geometry)

    try:
        extraction = method.extract(restored, secret_key, valid_region=region, force_length=payload.data_length)
        raw_bits, extracted_text, message = extraction.raw_bits, extraction.watermark, extraction.message
        success = extraction.valid and extracted_text == watermark_text
        if extraction.valid and not success:
            message = "Watermark terbaca tetapi isinya berbeda dari watermark asli."
    except WatermarkError as exc:
        raw_bits, extracted_text, message, success = np.zeros(len(payload.all_bits), np.uint8), "", str(exc), False

    row = {
        "attack_key": spec.key,
        "attack": spec.name,
        "parameter": spec.parameter,
        "psnr_after_attack": _psnr_after_attack(original, attacked, restored, output.geometry),
        "nc": calculate_nc(payload.all_bits, raw_bits),
        "ber": calculate_ber(payload.all_bits, raw_bits),
        "extracted_watermark": extracted_text,
        "status": "SUCCESS" if success else "FAIL",
        "message": message,
        "file": out_path.name,
        "file_sha256": file_sha256(out_path),
        "attacked_size": f"{attacked.shape[1]}x{attacked.shape[0]}",
        "short": spec.short,
        "seconds": round(time.perf_counter() - started, 3),
    }
    logger.info("Attack %s generated (%s, sha256=%s...) status=%s", spec.key, out_path.name, row["file_sha256"][:10], row["status"])
    return row


def find_duplicate_outputs(rows: List[Dict]) -> List[List[str]]:
    """Groups of attack keys whose output files are byte-identical (should be empty)."""
    seen: Dict[str, List[str]] = {}
    for row in rows:
        seen.setdefault(row["file_sha256"], []).append(row["attack_key"])
    return [keys for keys in seen.values() if len(keys) > 1]


def run_all_attacks(
    original: np.ndarray,
    watermarked: np.ndarray,
    method_key: str,
    secret_key: str,
    watermark_text: str,
    output_dir: Path,
    image_name: str = "image",
    progress: Optional[Callable[[str], None]] = None,
) -> List[Dict]:
    """Run: original(no attack), JPEG 90/70/50, crop, resize, noise, brightness, contrast.

    Setiap serangan ditulis ke file BERBEDA di ``output_dir``. Mengembalikan
    daftar baris hasil (dict) yang siap dipakai tabel / XLSX / grafik.
    """
    method = get_method(method_key)
    psnr_watermarked = calculate_psnr(original, watermarked)
    rows: List[Dict] = []
    for spec in build_attack_specs():
        if progress:
            progress(f"{image_name} | {method.label} | {spec.short}")
        out_path = Path(output_dir) / f"{image_name}_{method.key}_{spec.key}.{spec.extension}"
        row = run_single_attack(spec, original, watermarked, method.key, secret_key, watermark_text, out_path)
        row.update({"image": image_name, "method": method.label, "method_key": method.key, "psnr_watermarked": psnr_watermarked})
        rows.append(row)
    duplicates = find_duplicate_outputs(rows)
    if duplicates:
        logger.warning("Some attack outputs are byte-identical: %s", duplicates)
    return rows
