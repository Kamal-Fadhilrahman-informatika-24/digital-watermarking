import numpy as np
import pytest
from PIL import Image
from watermark.embed import embed_watermark
from watermark.extract import extract_watermark
from watermark.metrics import calculate_psnr, calculate_ber
from watermark.utils import text_to_bits
from watermark.attacks import attack_jpeg

TEXT = "237006001"


@pytest.fixture
def cover(tmp_path):
    yy, xx = np.mgrid[0:256, 0:256]
    base = 120 + 50 * np.sin(xx / 17) + 40 * np.cos(yy / 23) + np.random.default_rng(3).normal(0, 6, (256, 256))
    rgb = np.stack([base, base * 0.9, base * 0.8], axis=-1)
    path = tmp_path / "cover.png"
    Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).save(path)
    return str(path)


def test_embed_extract_roundtrip(cover, tmp_path):
    out = str(tmp_path / "wm.png")
    embed_watermark(cover, TEXT, "kunci-a", out)
    assert extract_watermark(out, "kunci-a", len(TEXT))[0] == TEXT


def test_output_size_same_and_psnr_above_30(cover, tmp_path):
    out = str(tmp_path / "wm.png")
    embed_watermark(cover, TEXT, "kunci-a", out)
    assert Image.open(out).size == Image.open(cover).size
    assert calculate_psnr(cover, out) > 30


def test_wrong_key_fails(cover, tmp_path):
    out = str(tmp_path / "wm.png")
    embed_watermark(cover, TEXT, "kunci-a", out)
    _, bits = extract_watermark(out, "kunci-salah", len(TEXT))
    assert calculate_ber(text_to_bits(TEXT), bits) > 0.25


def test_survives_jpeg_70(cover, tmp_path):
    out, atk = str(tmp_path / "wm.png"), str(tmp_path / "a.jpg")
    embed_watermark(cover, TEXT, "kunci-a", out)
    attack_jpeg(out, atk, 70)
    _, bits = extract_watermark(atk, "kunci-a", len(TEXT))
    assert calculate_ber(text_to_bits(TEXT), bits) < 0.1
