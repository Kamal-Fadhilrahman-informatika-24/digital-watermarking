"""Quality and robustness metrics: PSNR, NC and BER (semua dihitung dari data)."""

from __future__ import annotations

import math
from typing import Sequence, Union

import numpy as np

BitsLike = Union[Sequence[int], np.ndarray]


def calculate_mse(original: np.ndarray, other: np.ndarray) -> float:
    """Mean squared error between two images of identical shape."""
    if original.shape != other.shape:
        raise ValueError(
            f"Ukuran citra berbeda: {original.shape} vs {other.shape}."
        )
    diff = original.astype(np.float64) - other.astype(np.float64)
    return float(np.mean(diff * diff))


def calculate_psnr(original: np.ndarray, watermarked: np.ndarray, max_value: float = 255.0) -> float:
    """PSNR (dB) = 10 * log10(MAX^2 / MSE). Returns ``inf`` when MSE == 0."""
    mse = calculate_mse(original, watermarked)
    if mse == 0.0:
        return math.inf
    return float(10.0 * math.log10((max_value ** 2) / mse))


def _as_bits(bits: BitsLike) -> np.ndarray:
    return np.asarray(bits, dtype=np.uint8).ravel()


def calculate_ber(original_bits: BitsLike, extracted_bits: BitsLike) -> float:
    """Bit Error Rate = jumlah bit berbeda / total bit.

    Jika panjang berbeda, bit yang hilang dihitung sebagai error.
    """
    a, b = _as_bits(original_bits), _as_bits(extracted_bits)
    total = max(a.size, b.size)
    if total == 0:
        raise ValueError("Deret bit kosong.")
    n = min(a.size, b.size)
    errors = int(np.count_nonzero(a[:n] != b[:n])) + (total - n)
    return errors / total


def calculate_nc(original_bits: BitsLike, extracted_bits: BitsLike) -> float:
    """Normalized Correlation on binary watermark bits.

        NC = sum(w * w') / sqrt(sum(w^2) * sum(w'^2))

    Nilai 1.0 = identik. Catatan: untuk deret bit acak yang independen, NC biner
    berada di sekitar 0.5 (bukan 0), jadi baca NC bersama BER dan status.
    """
    a, b = _as_bits(original_bits), _as_bits(extracted_bits)
    total = max(a.size, b.size)
    if total == 0:
        raise ValueError("Deret bit kosong.")
    a = np.pad(a, (0, total - a.size)).astype(np.float64)
    b = np.pad(b, (0, total - b.size)).astype(np.float64)
    denominator = math.sqrt(float(np.sum(a * a)) * float(np.sum(b * b)))
    if denominator == 0.0:
        return 1.0 if np.array_equal(a, b) else 0.0
    return float(np.sum(a * b) / denominator)
