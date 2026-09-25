"""Pengujian watermarking DCT (robust, blind)."""

import inspect

import cv2
import numpy as np
import pytest

from watermark import config
from watermark.dct_watermark import embed_dct_watermark, extract_dct_watermark, max_watermark_bytes
from watermark.errors import CapacityError, ImageValidationError, WatermarkError
from watermark.metrics import calculate_ber, calculate_nc, calculate_psnr
from watermark.payload import encode_payload


@pytest.fixture(scope="module")
def embedded(cover, key, text):
    return embed_dct_watermark(cover, text, key)


def _luma(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)[:, :, 0].astype(np.float32)


def test_dct_embedding(cover, embedded):
    wm = embedded.image
    assert wm.shape == cover.shape and wm.dtype == np.uint8
    assert not np.array_equal(wm, cover), "embedding harus benar-benar mengubah piksel"
    psnr = calculate_psnr(cover, wm)
    assert psnr > 35.0, f"PSNR terlalu rendah: {psnr:.2f} dB"
    assert embedded.info["body_repetition"] >= config.MIN_BODY_REPETITION


def test_dct_never_modifies_dc_coefficient(cover, embedded):
    y0, y1 = _luma(cover), _luma(embedded.image)
    worst_dc, worst_mid = 0.0, 0.0
    for by in range(0, 64, 3):
        for bx in range(0, 64, 3):
            win = (slice(by * 8, by * 8 + 8), slice(bx * 8, bx * 8 + 8))
            a, b = cv2.dct(np.ascontiguousarray(y0[win])), cv2.dct(np.ascontiguousarray(y1[win]))
            worst_dc = max(worst_dc, abs(float(a[0, 0] - b[0, 0])))
            worst_mid = max(worst_mid, float(np.abs(a - b)[1:5, 1:5].max()))
    assert worst_dc < 1.0, "koefisien DC tidak boleh diubah (selain pembulatan piksel)"
    assert worst_mid > 5.0, "koefisien mid-frequency harus benar-benar diubah"


def test_dct_extraction(embedded, key, text):
    result = extract_dct_watermark(embedded.image, key)
    assert result.valid and result.header_valid and result.crc_valid
    assert result.watermark == text
    assert result.message == "Watermark berhasil dideteksi."
    payload = encode_payload(text)
    assert calculate_ber(payload.all_bits, result.raw_bits) == 0.0
    assert calculate_nc(payload.all_bits, result.raw_bits) == pytest.approx(1.0)


def test_dct_extraction_is_blind(embedded, key, text):
    params = inspect.signature(extract_dct_watermark).parameters
    assert not any("original" in name for name in params), "extractor tidak boleh meminta citra asli"
    ok, png = cv2.imencode(".png", embedded.image)  # simulasi: citra dibaca dari file
    reloaded = cv2.imdecode(png, cv2.IMREAD_COLOR)
    assert extract_dct_watermark(reloaded, key).watermark == text


def test_wrong_key(embedded, other_key, text):
    result = extract_dct_watermark(embedded.image, other_key)
    assert not result.valid
    assert result.watermark == ""
    assert "tidak" in result.message.lower()


def test_unmarked_image_has_no_watermark(cover, key):
    result = extract_dct_watermark(cover, key)
    assert not result.valid and result.watermark == ""


def test_key_determinism_same_key_same_output(cover, key, text, embedded):
    again = embed_dct_watermark(cover, text, key)
    assert np.array_equal(again.image, embedded.image)


def test_different_keys_produce_different_watermark_patterns(cover, embedded, other_key, text):
    """Header+body memenuhi hampir semua blok, jadi bandingkan POLA perubahannya:
    key berbeda -> pasangan koefisien & bit per blok berbeda -> pola selisih tidak berkorelasi."""
    other = embed_dct_watermark(cover, text, other_key)
    assert not np.array_equal(other.image, embedded.image)
    delta_a = (embedded.image.astype(np.float64) - cover).ravel()
    delta_b = (other.image.astype(np.float64) - cover).ravel()
    same_key = (embed_dct_watermark(cover, text, "kunci-uji-pytest-A").image.astype(np.float64) - cover).ravel()
    assert np.corrcoef(delta_a, same_key)[0, 1] > 0.999
    assert abs(np.corrcoef(delta_a, delta_b)[0, 1]) < 0.5


@pytest.mark.parametrize("secret", ["k1", "kunci panjang dengan spasi 123", "ÜñïçödÉ-üji"])
def test_various_keys_roundtrip(cover, text, secret):
    wm = embed_dct_watermark(cover, text, secret).image
    assert extract_dct_watermark(wm, secret).watermark == text


def test_utf8_watermark_roundtrip(cover, key):
    message = "Universitas Indonésia 日本語"
    wm = embed_dct_watermark(cover, message, key).image
    assert extract_dct_watermark(wm, key).watermark == message


def test_input_image_is_not_modified_in_place(cover, key, text):
    before = cover.copy()
    embed_dct_watermark(cover, text, key)
    assert np.array_equal(before, cover)


def test_capacity_error_on_small_image(cover, key):
    small = cover[:128, :128].copy()
    assert max_watermark_bytes(small.shape) == 0
    with pytest.raises(CapacityError):
        embed_dct_watermark(small, "KAMAL", key)


def test_image_below_minimum_side_is_rejected(cover, key):
    with pytest.raises(ImageValidationError):
        embed_dct_watermark(cover[:100, :300].copy(), "KAMAL", key)


def test_grayscale_image_is_rejected(cover, key):
    gray = cv2.cvtColor(cover, cv2.COLOR_BGR2GRAY)
    with pytest.raises(ImageValidationError):
        embed_dct_watermark(gray, "KAMAL", key)


def test_empty_key_and_empty_text_are_rejected(cover, key):
    with pytest.raises(WatermarkError):
        embed_dct_watermark(cover, "KAMAL", "")
    with pytest.raises(WatermarkError):
        embed_dct_watermark(cover, "  ", key)
    with pytest.raises(WatermarkError):
        extract_dct_watermark(cover, "")
