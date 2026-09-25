"""Pengujian metrik: MSE, PSNR, NC, BER (nilai dibandingkan dengan hitungan manual)."""

import math

import numpy as np
import pytest

from watermark.metrics import calculate_ber, calculate_mse, calculate_nc, calculate_psnr


def test_psnr_identical_images_is_infinite():
    image = np.full((16, 16, 3), 100, dtype=np.uint8)
    assert calculate_psnr(image, image.copy()) == math.inf


def test_psnr_matches_manual_formula():
    original = np.full((16, 16, 3), 100, dtype=np.uint8)
    for delta in (1, 5, 10):
        changed = original + delta
        expected = 10 * math.log10(255 ** 2 / delta ** 2)
        assert calculate_mse(original, changed) == pytest.approx(delta ** 2)
        assert calculate_psnr(original, changed) == pytest.approx(expected, abs=1e-9)


def test_psnr_decreases_when_distortion_increases():
    rng = np.random.default_rng(1)
    original = rng.integers(0, 256, (64, 64, 3), dtype=np.uint8)
    values = []
    for sigma in (2, 8, 20):
        noisy = np.clip(original + rng.normal(0, sigma, original.shape), 0, 255).astype(np.uint8)
        values.append(calculate_psnr(original, noisy))
    assert values[0] > values[1] > values[2]


def test_psnr_rejects_different_shapes():
    with pytest.raises(ValueError):
        calculate_psnr(np.zeros((8, 8, 3), np.uint8), np.zeros((8, 9, 3), np.uint8))


def test_nc_identical_is_one():
    bits = [1, 0, 1, 1, 0, 0, 1, 0]
    assert calculate_nc(bits, bits) == pytest.approx(1.0)


def test_nc_matches_manual_formula():
    a, b = [1, 1, 0, 0], [1, 0, 0, 0]
    # sum(a*b)=1 ; sqrt(sum(a^2)*sum(b^2)) = sqrt(2*1)
    assert calculate_nc(a, b) == pytest.approx(1 / math.sqrt(2))


def test_nc_drops_when_bits_are_flipped():
    rng = np.random.default_rng(3)
    original = rng.integers(0, 2, 400)
    previous = 1.0
    for n_flips in (10, 60, 150):
        damaged = original.copy()
        idx = rng.choice(400, n_flips, replace=False)
        damaged[idx] ^= 1
        value = calculate_nc(original, damaged)
        assert value < previous
        previous = value


def test_nc_handles_all_zero_sequences():
    assert calculate_nc([0, 0, 0], [0, 0, 0]) == 1.0
    assert calculate_nc([1, 1, 0], [0, 0, 0]) == 0.0


def test_ber_identical_is_zero():
    assert calculate_ber([1, 0, 1, 0], [1, 0, 1, 0]) == 0.0


def test_ber_all_flipped_is_one():
    assert calculate_ber([1, 0, 1, 0], [0, 1, 0, 1]) == 1.0


def test_ber_matches_manual_count():
    original = [1, 0, 1, 1, 0, 0, 1, 0]
    extracted = [1, 1, 1, 1, 0, 1, 1, 0]  # 2 bit berbeda dari 8
    assert calculate_ber(original, extracted) == pytest.approx(2 / 8)


def test_ber_counts_missing_bits_as_errors():
    assert calculate_ber([1, 1, 1, 1], [1, 1]) == pytest.approx(0.5)


def test_bit_metrics_reject_empty_input():
    with pytest.raises(ValueError):
        calculate_ber([], [])
    with pytest.raises(ValueError):
        calculate_nc([], [])
