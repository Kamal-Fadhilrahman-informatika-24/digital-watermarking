"""Pengujian serangan gambar dan mesin pengujian (attack engine)."""

import math

import cv2
import numpy as np
import pytest

from watermark import config
from watermark.attack_engine import find_duplicate_outputs, run_all_attacks
from watermark.attacks import (
    brightness_attack,
    build_attack_specs,
    contrast_attack,
    crop_attack,
    crop_box,
    gaussian_noise_attack,
    jpeg_attack,
    jpeg_compress,
    resize_attack,
    restore_geometry,
)
from watermark.dct_watermark import embed_dct_watermark
from watermark.lsb_watermark import embed_lsb_watermark
from watermark.metrics import calculate_psnr
from watermark.utils import read_image

ATTACK_KEYS = ["none", "jpeg_90", "jpeg_70", "jpeg_50", "crop", "resize", "noise", "brightness", "contrast"]


# ------------------------------------------------------------- serangan dasar
def test_jpeg_attack(cover):
    sizes, psnrs = [], []
    for quality in (90, 70, 50):
        data = jpeg_compress(cover, quality)
        assert data[:3] == b"\xff\xd8\xff", "harus benar-benar berkas JPEG"
        decoded = jpeg_attack(cover, quality)
        assert decoded.shape == cover.shape and not np.array_equal(decoded, cover)
        sizes.append(len(data))
        psnrs.append(calculate_psnr(cover, decoded))
    assert sizes[0] > sizes[1] > sizes[2], "kualitas lebih rendah -> file lebih kecil"
    assert psnrs[0] > psnrs[1] > psnrs[2]


def test_jpeg_quality_out_of_range_is_rejected(cover):
    for bad in (0, 101):
        with pytest.raises(ValueError):
            jpeg_compress(cover, bad)


def test_resize_attack(cover):
    small = resize_attack(cover)
    assert small.shape[:2] == (round(512 * config.RESIZE_SCALE), round(512 * config.RESIZE_SCALE))
    restored, region = restore_geometry(small, {"type": "resize", "orig_w": 512, "orig_h": 512})
    assert restored.shape == cover.shape and region is None


def test_crop_attack(cover):
    cropped, (x0, y0, x1, y1) = crop_attack(cover)
    assert x0 % 8 == 0 and y0 % 8 == 0, "offset crop harus selaras dengan grid blok 8x8"
    assert np.array_equal(cropped, cover[y0:y1, x0:x1])
    removed = 1 - (cropped.shape[0] * cropped.shape[1]) / (512 * 512)
    assert 0.05 < removed < 0.25
    assert crop_box(512, 512, config.CROP_RATIO) == (x0, y0, x1, y1)


def test_restore_geometry_for_crop_marks_valid_region(cover):
    cropped, box = crop_attack(cover)
    geometry = {"type": "crop", "x0": box[0], "y0": box[1], "orig_w": 512, "orig_h": 512}
    canvas, region = restore_geometry(cropped, geometry)
    assert canvas.shape == cover.shape and region == box
    assert np.array_equal(canvas[box[1]:box[3], box[0]:box[2]], cropped)
    assert canvas[0, 0].sum() == 0  # area yang hilang dikosongkan


def test_gaussian_noise_attack_statistics_and_seed():
    flat = np.full((256, 256, 3), 128, dtype=np.uint8)
    noisy = gaussian_noise_attack(flat, sigma=5.0, seed=7)
    residual = noisy.astype(np.float64) - 128
    assert abs(residual.mean()) < 0.1
    assert residual.std() == pytest.approx(5.0, abs=0.15)
    assert np.array_equal(noisy, gaussian_noise_attack(flat, sigma=5.0, seed=7))
    assert not np.array_equal(noisy, gaussian_noise_attack(flat, sigma=5.0, seed=8))


def test_brightness_attack_exact_values_and_clipping():
    image = np.array([[[10, 100, 250]]], dtype=np.uint8)
    assert brightness_attack(image, 20).tolist() == [[[30, 120, 255]]]
    assert brightness_attack(image, -20).tolist() == [[[0, 80, 230]]]


def test_contrast_attack_exact_values():
    image = np.array([[[128, 100, 200]]], dtype=np.uint8)
    assert contrast_attack(image, 1.2).tolist() == [[[128, 94, 214]]]  # (v-128)*1.2+128


# ----------------------------------------------------------- daftar serangan
def test_nine_attack_specs_are_defined():
    specs = build_attack_specs()
    assert [s.key for s in specs] == ATTACK_KEYS
    assert len({s.short for s in specs}) == len(specs)


# ------------------------------------------------------------- attack engine
@pytest.fixture(scope="module")
def dct_rows(cover, key, text, tmp_path_factory):
    wm = embed_dct_watermark(cover, text, key).image
    out = tmp_path_factory.mktemp("attacks_dct")
    return run_all_attacks(cover, wm, "dct", key, text, out, image_name="uji"), out


@pytest.fixture(scope="module")
def lsb_rows(cover, key, text, tmp_path_factory):
    wm = embed_lsb_watermark(cover, text, key).image
    out = tmp_path_factory.mktemp("attacks_lsb")
    return run_all_attacks(cover, wm, "lsb", key, text, out, image_name="uji"), out


def test_engine_runs_all_attacks_and_writes_distinct_files(dct_rows):
    rows, out = dct_rows
    assert [r["attack_key"] for r in rows] == ATTACK_KEYS
    files = sorted(p.name for p in out.iterdir())
    assert len(files) == 9
    assert find_duplicate_outputs(rows) == [], "setiap serangan harus menghasilkan file yang berbeda"
    jpg = [p for p in out.iterdir() if p.suffix == ".jpg"]
    assert len(jpg) == 3 and all(p.read_bytes()[:3] == b"\xff\xd8\xff" for p in jpg)


def test_engine_rows_have_real_metrics(dct_rows, cover):
    rows, out = dct_rows
    by_key = {r["attack_key"]: r for r in rows}
    for row in rows:
        assert 0.0 <= row["ber"] <= 1.0 and 0.0 <= row["nc"] <= 1.0 + 1e-9
        assert row["status"] in {"SUCCESS", "FAIL"}
        assert (out / row["file"]).exists()
    # PSNR benar-benar dihitung ulang dari file hasil serangan
    noise = read_image(out / by_key["noise"]["file"])
    assert by_key["noise"]["psnr_after_attack"] == pytest.approx(calculate_psnr(cover, noise))
    # serangan lebih berat -> PSNR lebih rendah
    assert by_key["jpeg_90"]["psnr_after_attack"] > by_key["jpeg_70"]["psnr_after_attack"] > by_key["jpeg_50"]["psnr_after_attack"]
    assert math.isfinite(by_key["none"]["psnr_watermarked"])


def test_dct_is_robust_against_required_attacks(dct_rows):
    rows, _ = dct_rows
    status = {r["attack_key"]: r["status"] for r in rows}
    for attack in ("none", "jpeg_90", "jpeg_70", "jpeg_50", "crop", "resize", "noise"):
        assert status[attack] == "SUCCESS", f"DCT gagal pada {attack}"
    for row in rows:
        if row["status"] == "SUCCESS":
            assert row["ber"] == 0.0 and row["extracted_watermark"] == "KAMAL FADHILRAHMAN"


def test_lsb_is_fragile_in_engine(lsb_rows):
    rows, _ = lsb_rows
    status = {r["attack_key"]: r["status"] for r in rows}
    assert status["none"] == "SUCCESS"
    for attack in ("jpeg_90", "jpeg_70", "jpeg_50", "resize", "noise", "contrast"):
        assert status[attack] == "FAIL", f"LSB seharusnya gagal pada {attack}"


def test_wrong_key_fails_every_attack(cover, key, other_key, text, tmp_path):
    wm = embed_dct_watermark(cover, text, key).image
    rows = run_all_attacks(cover, wm, "dct", other_key, text, tmp_path, image_name="salah")
    assert all(r["status"] == "FAIL" for r in rows)
