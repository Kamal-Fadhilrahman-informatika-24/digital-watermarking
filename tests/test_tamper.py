"""Pengujian peta lokalisasi tamper (fragile block authentication) untuk LSB.

Menguji Bagian 3 Topik C: "Untuk jalur fragile, tampilkan peta area yang
terdeteksi diubah."
"""

from __future__ import annotations

import cv2
import numpy as np

from watermark.lsb_watermark import embed_lsb_watermark, extract_lsb_watermark
from watermark.tamper import detect_tamper_map, embed_tamper_watermark, encode_png_data_uri, render_tamper_overlay


def _embed_full(cover: np.ndarray, text: str, key: str):
    """Tanam payload teks lalu bit autentikasi tamper, seperti alur service.embed_upload.

    Return (citra_akhir, payload_positions) - payload_positions harus dipakai lagi
    saat deteksi (persis seperti ``service.detect_bytes`` memakai
    ``extraction.reserved_positions``), karena bit payload teks juga menempati
    sebagian LSB dan harus dikecualikan secara konsisten dari verifikasi blok.
    """
    embedded = embed_lsb_watermark(cover, text, key)
    positions = embedded.info["payload_positions"]
    final = embed_tamper_watermark(embedded.image, key, reserved_positions=positions)
    return final, positions


def test_clean_image_has_no_tampered_blocks(cover, key, text):
    watermarked, positions = _embed_full(cover, text, key)
    tamper = detect_tamper_map(watermarked, key, reserved_positions=positions)
    assert tamper.tampered_blocks == 0
    assert tamper.total_blocks > 0
    assert tamper.tampered_ratio == 0.0


def test_localized_edit_is_localized_in_the_map(cover, key, text):
    watermarked, positions = _embed_full(cover, text, key)
    h, w = watermarked.shape[:2]
    tampered_img = watermarked.copy()
    # Corat-coret kotak solid di pojok kiri-atas (25% lebar dan tinggi).
    cv2.rectangle(tampered_img, (0, 0), (w // 4, h // 4), (0, 255, 0), thickness=-1)

    tamper = detect_tamper_map(tampered_img, key, reserved_positions=positions)
    assert tamper.tampered_blocks > 0

    bs = tamper.block_size
    max_row = (h // 4) // bs + 1
    max_col = (w // 4) // bs + 1
    # Semua blok yang ditandai harus berada di dalam (atau sangat dekat) area yang dirusak.
    rows, cols = np.where(tamper.tampered)
    assert rows.max() <= max_row
    assert cols.max() <= max_col
    # Blok yang jauh dari area yang dirusak (pojok kanan-bawah) harus tetap bersih.
    assert not tamper.tampered[-1, -1]


def test_wrong_key_flags_almost_every_block(cover, key, other_key, text):
    watermarked, positions = _embed_full(cover, text, key)
    tamper = detect_tamper_map(watermarked, other_key, reserved_positions=positions)
    # Tanpa key yang benar, verifikasi HMAC gagal di (hampir) semua blok -> sinyal
    # yang jelas bahwa citra tidak bisa diautentikasi dengan key ini.
    assert tamper.tampered_ratio > 0.95


def test_jpeg_resave_breaks_fragile_map(cover, key, text):
    """Sesuai spesifikasi: LSB fragile harus rapuh terhadap kompresi JPEG ulang."""
    watermarked, positions = _embed_full(cover, text, key)
    ok, buf = cv2.imencode(".jpg", watermarked, [cv2.IMWRITE_JPEG_QUALITY, 90])
    assert ok
    resaved = cv2.imdecode(np.frombuffer(buf.tobytes(), dtype=np.uint8), cv2.IMREAD_COLOR)

    tamper = detect_tamper_map(resaved, key, reserved_positions=positions)
    assert tamper.tampered_ratio > 0.9


def test_extract_lsb_reports_payload_positions_for_tamper_map(cover, key, text):
    embedded = embed_lsb_watermark(cover, text, key)
    final = embed_tamper_watermark(embedded.image, key, reserved_positions=embedded.info["payload_positions"])
    extraction = extract_lsb_watermark(final, key)
    assert extraction.valid
    assert extraction.reserved_positions is not None
    assert len(extraction.reserved_positions) == len(embedded.info["payload_positions"])


def test_overlay_and_data_uri(cover, key, text):
    watermarked, positions = _embed_full(cover, text, key)
    tampered_img = watermarked.copy()
    cv2.rectangle(tampered_img, (0, 0), (32, 32), (0, 255, 0), thickness=-1)
    tamper = detect_tamper_map(tampered_img, key, reserved_positions=positions)

    overlay = render_tamper_overlay(tampered_img, tamper)
    assert overlay.shape == tampered_img.shape

    uri = encode_png_data_uri(overlay)
    assert uri.startswith("data:image/png;base64,")
