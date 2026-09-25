"""Pengujian LSB fragile (fitur pengayaan) dan perbandingannya dengan DCT."""

import numpy as np
import pytest

from watermark.attacks import brightness_attack, gaussian_noise_attack, jpeg_attack
from watermark.dct_watermark import embed_dct_watermark, extract_dct_watermark
from watermark.errors import WatermarkError
from watermark.lsb_watermark import embed_lsb_watermark, extract_lsb_watermark
from watermark.metrics import calculate_psnr


@pytest.fixture(scope="module")
def lsb_embedded(cover, key, text):
    return embed_lsb_watermark(cover, text, key)


def test_lsb_embedding(cover, lsb_embedded, key, text):
    diff = np.abs(cover.astype(int) - lsb_embedded.image.astype(int))
    assert diff.max() == 1, "LSB hanya boleh mengubah nilai piksel sebesar 1"
    assert 0 < np.count_nonzero(diff) <= lsb_embedded.n_bits
    assert calculate_psnr(cover, lsb_embedded.image) > 50.0
    result = extract_lsb_watermark(lsb_embedded.image, key)
    assert result.valid and result.watermark == text


def test_lsb_wrong_key(lsb_embedded, other_key):
    result = extract_lsb_watermark(lsb_embedded.image, other_key)
    assert not result.valid and result.watermark == ""


def test_lsb_positions_depend_on_key(cover, text, key, other_key):
    a = embed_lsb_watermark(cover, text, key).image
    b = embed_lsb_watermark(cover, text, other_key).image
    assert not np.array_equal(a, b)


def test_lsb_is_deterministic(cover, text, key, lsb_embedded):
    assert np.array_equal(embed_lsb_watermark(cover, text, key).image, lsb_embedded.image)


def test_lsb_is_fragile_against_jpeg(lsb_embedded, key):
    for quality in (90, 70, 50):
        result = extract_lsb_watermark(jpeg_attack(lsb_embedded.image, quality), key)
        assert not result.valid, f"LSB seharusnya rapuh terhadap JPEG {quality}"


def test_lsb_is_fragile_against_noise(lsb_embedded, key):
    assert not extract_lsb_watermark(gaussian_noise_attack(lsb_embedded.image), key).valid


def test_dct_survives_what_lsb_does_not(cover, key, text):
    """Perbandingan nyata pada citra dan attack yang sama."""
    dct = embed_dct_watermark(cover, text, key).image
    lsb = embed_lsb_watermark(cover, text, key).image
    for attack in (lambda im: jpeg_attack(im, 70), gaussian_noise_attack):
        assert extract_dct_watermark(attack(dct), key).watermark == text
        assert not extract_lsb_watermark(attack(lsb), key).valid


def test_lsb_without_attack_is_fine_but_brightness_breaks_most_bits(lsb_embedded, key):
    assert extract_lsb_watermark(lsb_embedded.image, key).valid
    shifted = brightness_attack(lsb_embedded.image, 1)  # +1 membalik semua LSB
    assert not extract_lsb_watermark(shifted, key).valid


def test_lsb_input_validation(cover, key):
    with pytest.raises(WatermarkError):
        embed_lsb_watermark(cover, "KAMAL", "")
    with pytest.raises(WatermarkError):
        embed_lsb_watermark(cover, "", key)
    with pytest.raises(WatermarkError):
        extract_lsb_watermark(cover, "")
