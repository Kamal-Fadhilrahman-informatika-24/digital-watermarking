"""Shared helpers: image validation/IO, safe file handling, JSON helpers."""

from __future__ import annotations

import hashlib
import io
import logging
import math
import re
import time
import uuid
from pathlib import Path
from typing import Any, Tuple

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError

from . import config
from .errors import ImageValidationError

logger = logging.getLogger(__name__)

MAX_PIXELS = 25_000_000  # cegah decompression bomb
_JOB_ID_RE = re.compile(r"^[0-9a-f]{12}$")
_SIGNATURES = (b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff")


# ------------------------------------------------------------- validation
def allowed_file(filename: str) -> bool:
    """True if the extension is one of PNG/JPG/JPEG."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in config.ALLOWED_EXTENSIONS


def check_image(image: np.ndarray) -> None:
    """Validate an in-memory BGR image before watermarking."""
    if image is None or image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8:
        raise ImageValidationError("Citra harus berupa gambar berwarna 8-bit (BGR).")
    if min(image.shape[:2]) < config.MIN_IMAGE_SIDE:
        raise ImageValidationError(
            f"Citra terlalu kecil. Sisi terpendek minimal {config.MIN_IMAGE_SIDE} piksel."
        )


def decode_image(data: bytes) -> np.ndarray:
    """Validate uploaded bytes and decode them to a BGR uint8 image.

    Pemeriksaan: tidak kosong, signature PNG/JPEG, Pillow bisa membaca, ukuran
    piksel wajar, OpenCV bisa decode. Tidak mempercayai ekstensi file saja.
    """
    if not data:
        raise ImageValidationError("File kosong. Pilih file gambar yang valid.")
    if not data.startswith(_SIGNATURES):
        raise ImageValidationError("File bukan gambar PNG/JPG yang valid.")
    try:
        with Image.open(io.BytesIO(data)) as probe:
            width, height = probe.size
            probe.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as exc:
        raise ImageValidationError("Gambar rusak atau tidak dapat dibaca.") from exc
    if width * height > MAX_PIXELS:
        raise ImageValidationError("Resolusi gambar terlalu besar untuk diproses.")
    image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ImageValidationError("Gambar rusak atau tidak dapat dibaca.")
    return image


def limit_image_size(image: np.ndarray, max_side: int = config.MAX_PROCESS_SIDE) -> Tuple[np.ndarray, bool, Tuple[int, int]]:
    """Downscale (keeping aspect ratio) if the longest side exceeds ``max_side``.

    Returns (image, was_resized, (original_width, original_height)).
    """
    h, w = image.shape[:2]
    longest = max(h, w)
    if longest <= max_side:
        return image, False, (w, h)
    scale = max_side / longest
    resized = cv2.resize(image, (int(round(w * scale)), int(round(h * scale))), interpolation=cv2.INTER_AREA)
    return resized, True, (w, h)


# --------------------------------------------------------------- file IO
def save_png(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), image):
        raise ImageValidationError("Gagal menyimpan gambar.")


def read_image(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise ImageValidationError(f"Gagal membaca file: {path.name}")
    return image


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def new_job_id() -> str:
    return uuid.uuid4().hex[:12]


def is_valid_job_id(job_id: str) -> bool:
    return bool(_JOB_ID_RE.match(job_id or ""))


def cleanup_old_files(directory: Path, max_age_hours: float = config.TEMP_FILE_MAX_AGE_HOURS, pattern: str = "*") -> int:
    """Delete files/folders matching ``pattern`` older than ``max_age_hours``.

    File tersembunyi (.gitkeep) tidak pernah dihapus. Returns jumlah item terhapus.
    """
    if not directory.exists():
        return 0
    cutoff = time.time() - max_age_hours * 3600
    removed = 0
    for item in directory.glob(pattern):
        if item.name.startswith("."):
            continue
        try:
            if item.stat().st_mtime < cutoff:
                if item.is_dir():
                    for child in sorted(item.rglob("*"), reverse=True):
                        child.unlink() if child.is_file() else child.rmdir()
                    item.rmdir()
                else:
                    item.unlink()
                removed += 1
        except OSError:  # pragma: no cover - best effort cleanup
            logger.warning("Could not remove temporary item %s", item.name)
    return removed


# ------------------------------------------------------------------ misc
def json_safe(value: Any) -> Any:
    """Convert numpy types / inf / nan into JSON-friendly values."""
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return "inf" if value > 0 else None
    return value


def format_psnr(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, str) or (isinstance(value, float) and math.isinf(value)):
        return "∞ dB"
    return f"{value:.2f} dB"
