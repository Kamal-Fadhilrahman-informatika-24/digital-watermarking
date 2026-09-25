"""Dataset evaluation: embed + attack + metrics for many images and methods."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

from . import config
from .attack_engine import run_all_attacks
from .attacks import build_attack_specs
from .errors import WatermarkError
from .methods import get_method
from .metrics import calculate_psnr
from .synthetic import KINDS, make_synthetic_image
from .utils import decode_image, file_sha256, json_safe, limit_image_size, save_png

logger = logging.getLogger(__name__)


def generate_synthetic_dataset(dataset_dir: Path = config.DATASET_DIR, size: int = 512, overwrite: bool = False) -> List[Path]:
    """Create image01..image05.png (fallback dataset) if they are missing."""
    dataset_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for index, (name, kind) in enumerate(zip(config.DATASET_IMAGE_NAMES, KINDS)):
        path = dataset_dir / name
        if overwrite or not path.exists():
            save_png(path, make_synthetic_image(kind, size, size, seed=index))
            written.append(path)
    return written


def list_dataset_images(dataset_dir: Path = config.DATASET_DIR) -> List[Path]:
    if not dataset_dir.exists():
        return []
    return sorted(p for p in dataset_dir.iterdir() if p.suffix.lower().lstrip(".") in config.ALLOWED_EXTENSIONS)


def evaluate_dataset(
    dataset_dir: Path,
    secret_key: str,
    watermark_text: str,
    methods: Sequence[str] = ("dct", "lsb"),
    watermarked_dir: Path = config.TEST_DATA_DIR / "watermarked",
    attack_dir: Path = config.TEST_DATA_DIR / "attacks",
    progress: Optional[Callable[[str], None]] = None,
) -> Dict:
    """Run the full experiment on every image in ``dataset_dir``.

    Watermark, secret key dan attack sama untuk semua citra dan semua metode.
    Secret key tidak disimpan di hasil.
    """
    images = list_dataset_images(dataset_dir)
    if not images:
        raise WatermarkError("Dataset kosong. Jalankan: python scripts/generate_test_dataset.py")
    started = time.perf_counter()
    rows: List[Dict] = []
    dataset: List[Dict] = []
    for path in images:
        raw = path.read_bytes()
        original, resized, (ow, oh) = limit_image_size(decode_image(raw))
        dataset.append({
            "image": path.stem, "file": path.name, "width": original.shape[1], "height": original.shape[0],
            "size_kb": round(len(raw) / 1024, 1), "sha256": file_sha256(path)[:12],
            "note": "di-resize untuk pemrosesan" if resized else f"asli {ow}x{oh}",
        })
        for method_key in methods:
            method = get_method(method_key)
            logger.info("Embedding %s with %s", path.stem, method.label)
            embedded = method.embed(original, watermark_text, secret_key)
            save_png(watermarked_dir / method.key / f"{path.stem}.png", embedded.image)
            rows.extend(run_all_attacks(
                original, embedded.image, method.key, secret_key, watermark_text,
                attack_dir / method.key, image_name=path.stem, progress=progress,
            ))
    return {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "watermark_text": watermark_text,
        "methods": [get_method(m).label for m in methods],
        "rows": rows,
        "dataset": dataset,
        "attacks": [{"key": s.key, "name": s.name, "parameter": s.parameter, "short": s.short} for s in build_attack_specs()],
        "config": {
            "embed_strength": config.EMBED_STRENGTH,
            "coefficient_pairs": [list(map(list, p)) for p in config.COEFFICIENT_PAIRS],
            "header_repetition": config.HEADER_REPETITION,
            "block_size": config.BLOCK_SIZE,
            "jpeg_qualities": list(config.JPEG_QUALITIES),
            "crop_ratio": config.CROP_RATIO,
            "resize_scale": config.RESIZE_SCALE,
            "noise_sigma": config.NOISE_SIGMA,
            "brightness_delta": config.BRIGHTNESS_DELTA,
            "contrast_factor": config.CONTRAST_FACTOR,
        },
        "seconds": round(time.perf_counter() - started, 1),
    }


def save_results_json(results: Dict, path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(results), indent=2, ensure_ascii=False), encoding="utf-8")


def load_results_json(path) -> Optional[Dict]:
    path = Path(path)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    for row in data.get("rows", []):  # kembalikan "inf" -> float inf
        for key in ("psnr_watermarked", "psnr_after_attack"):
            if row.get(key) == "inf":
                row[key] = float("inf")
    return data
