"""Image attacks used for robustness testing.

Setiap serangan benar-benar mengubah data piksel (bukan hanya nama).
Parameter serangan berasal dari ``watermark/config.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

import cv2
import numpy as np

from . import config
from .errors import ImageValidationError
from .results import Region


# ------------------------------------------------------------ basic attacks
def jpeg_compress(image: np.ndarray, quality: int) -> bytes:
    """Encode ``image`` as a real JPEG at the given quality and return the bytes."""
    if not 1 <= int(quality) <= 100:
        raise ValueError("Kualitas JPEG harus 1-100.")
    ok, buffer = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), int(quality)])
    if not ok:
        raise ImageValidationError("Gagal melakukan kompresi JPEG.")
    return buffer.tobytes()


def jpeg_attack(image: np.ndarray, quality: int) -> np.ndarray:
    """JPEG compress + decode (the decoded pixels are what a detector would see)."""
    data = jpeg_compress(image, quality)
    return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)


def crop_box(height: int, width: int, ratio: float) -> Tuple[int, int, int, int]:
    """Crop box (x0, y0, x1, y1): ``ratio`` of width/height removed, split over both sides.

    Offset kiri/atas dibulatkan ke kelipatan 8 piksel agar grid blok DCT tetap
    selaras (dijelaskan di README, bagian Cropping).
    """
    cut_x = max(BLOCK, int(round(width * ratio / 2 / BLOCK)) * BLOCK)
    cut_y = max(BLOCK, int(round(height * ratio / 2 / BLOCK)) * BLOCK)
    return cut_x, cut_y, width - cut_x, height - cut_y


BLOCK = config.BLOCK_SIZE


def crop_attack(image: np.ndarray, ratio: float = config.CROP_RATIO) -> Tuple[np.ndarray, Tuple[int, int, int, int]]:
    """Cut a border from all four sides. Returns (cropped image, box)."""
    h, w = image.shape[:2]
    x0, y0, x1, y1 = crop_box(h, w, ratio)
    return image[y0:y1, x0:x1].copy(), (x0, y0, x1, y1)


def resize_attack(image: np.ndarray, scale: float = config.RESIZE_SCALE) -> np.ndarray:
    """Down-scale the image to ``scale`` of its size."""
    h, w = image.shape[:2]
    return cv2.resize(image, (max(1, int(round(w * scale))), max(1, int(round(h * scale)))), interpolation=cv2.INTER_AREA)


def gaussian_noise_attack(image: np.ndarray, sigma: float = config.NOISE_SIGMA, seed: int = config.NOISE_SEED) -> np.ndarray:
    """Add zero-mean Gaussian noise (std ``sigma``) to every channel."""
    rng = np.random.default_rng(seed)
    noisy = image.astype(np.float64) + rng.normal(0.0, sigma, image.shape)
    return np.clip(np.rint(noisy), 0, 255).astype(np.uint8)


def brightness_attack(image: np.ndarray, delta: int = config.BRIGHTNESS_DELTA) -> np.ndarray:
    """Add ``delta`` to every channel (clipped to 0..255)."""
    return np.clip(image.astype(np.int16) + int(delta), 0, 255).astype(np.uint8)


def contrast_attack(image: np.ndarray, factor: float = config.CONTRAST_FACTOR) -> np.ndarray:
    """Scale contrast around mid-gray: out = (in - 128) * factor + 128."""
    return np.clip(np.rint((image.astype(np.float64) - 128.0) * factor + 128.0), 0, 255).astype(np.uint8)


# --------------------------------------------------- attack registry / engine
@dataclass(frozen=True)
class AttackOutput:
    image: np.ndarray
    geometry: Optional[Dict[str, int]] = None  # info untuk memulihkan geometri saat deteksi


@dataclass(frozen=True)
class AttackSpec:
    key: str
    name: str
    parameter: str
    extension: str
    apply: Callable[[np.ndarray], AttackOutput]
    jpeg_quality: Optional[int] = None
    short: str = ""  # label pendek untuk grafik


def _plain(fn: Callable[[np.ndarray], np.ndarray]) -> Callable[[np.ndarray], AttackOutput]:
    return lambda img: AttackOutput(fn(img))


def _crop(img: np.ndarray) -> AttackOutput:
    cropped, (x0, y0, x1, y1) = crop_attack(img)
    return AttackOutput(cropped, {"type": "crop", "x0": x0, "y0": y0, "orig_w": img.shape[1], "orig_h": img.shape[0]})


def _resize(img: np.ndarray) -> AttackOutput:
    return AttackOutput(resize_attack(img), {"type": "resize", "orig_w": img.shape[1], "orig_h": img.shape[0]})


def build_attack_specs() -> list:
    """The nine test conditions: no attack + 8 attacks (JPEG x3, crop, resize, noise, brightness, contrast)."""
    specs = [AttackSpec("none", "Original (No Attack)", "-", "png", _plain(lambda img: img.copy()), short="No attack")]
    for q in config.JPEG_QUALITIES:
        specs.append(AttackSpec(f"jpeg_{q}", "JPEG", f"Quality {q}", "jpg", _plain(lambda img, q=q: jpeg_attack(img, q)), jpeg_quality=q, short=f"JPEG {q}"))
    pct = int(round(config.CROP_RATIO * 100))
    scale_pct = int(round(config.RESIZE_SCALE * 100))
    contrast_pct = int(round((config.CONTRAST_FACTOR - 1) * 100))
    specs += [
        AttackSpec("crop", "Cropping", f"Crop {pct}% (dari 4 sisi)", "png", _crop, short=f"Crop {pct}%"),
        AttackSpec("resize", "Resize", f"{scale_pct}% dari ukuran asli", "png", _resize, short=f"Resize {scale_pct}%"),
        AttackSpec("noise", "Gaussian Noise", f"sigma={config.NOISE_SIGMA:g}", "png", _plain(gaussian_noise_attack), short=f"Noise s={config.NOISE_SIGMA:g}"),
        AttackSpec("brightness", "Brightness", f"{config.BRIGHTNESS_DELTA:+d}", "png", _plain(brightness_attack), short=f"Bright {config.BRIGHTNESS_DELTA:+d}"),
        AttackSpec("contrast", "Contrast", f"x{config.CONTRAST_FACTOR:g} (+{contrast_pct}%)", "png", _plain(contrast_attack), short=f"Contrast +{contrast_pct}%"),
    ]
    return specs


def save_attack_image(spec: AttackSpec, image: np.ndarray, path: Path) -> None:
    """Write the attacked image to disk (real JPEG file for JPEG attacks)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if spec.jpeg_quality is not None:
        path.write_bytes(jpeg_compress(image, spec.jpeg_quality))
    else:
        if not cv2.imwrite(str(path), image):
            raise ImageValidationError(f"Gagal menyimpan file serangan: {path.name}")


def restore_geometry(image: np.ndarray, geometry: Optional[Dict[str, int]]) -> Tuple[np.ndarray, Optional[Region]]:
    """Prepare an attacked image for detection.

    * crop   : tempel kembali pada kanvas ukuran asli di posisi semula;
               area yang hilang ditandai sebagai *erasure* (valid_region).
    * resize : skalakan kembali ke ukuran asli (INTER_CUBIC).
    Strategi ini mengasumsikan detektor mengetahui ukuran asli (disimpan sebagai
    metadata) - lihat README bagian Cropping/Resize.
    """
    if not geometry:
        return image, None
    ow, oh = geometry["orig_w"], geometry["orig_h"]
    if geometry["type"] == "resize":
        return cv2.resize(image, (ow, oh), interpolation=cv2.INTER_CUBIC), None
    if geometry["type"] == "crop":
        canvas = np.zeros((oh, ow, 3), dtype=np.uint8)
        x0, y0 = geometry["x0"], geometry["y0"]
        h, w = image.shape[:2]
        canvas[y0:y0 + h, x0:x0 + w] = image
        return canvas, (x0, y0, x0 + w, y0 + h)
    raise ValueError(f"Jenis geometri tidak dikenal: {geometry['type']}")
