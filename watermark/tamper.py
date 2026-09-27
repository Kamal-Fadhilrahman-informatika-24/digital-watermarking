"""Peta lokalisasi tamper (fragile block authentication) untuk jalur LSB.

Ini terpisah dari payload watermark (teks identitas pemilik). Untuk setiap
blok BS x BS piksel pada citra, modul ini menanam beberapa "check bit" yang
diturunkan dari:

    - secret key (via HMAC-SHA256, sehingga tidak bisa dipalsukan tanpa key)
    - indeks blok (agar blok yang identik tetap punya check bit berbeda)
    - isi 7 bit teratas (MSB7) semua piksel pada blok tersebut

Check bit ditanam ke LSB piksel-piksel *bebas* pada blok yang sama, yaitu
piksel yang tidak dipakai payload teks watermark. Karena hash hanya
bergantung pada MSB7, penulisan bit LSB apa pun (baik oleh payload watermark
maupun oleh check bit itu sendiri) tidak pernah mengubah hasil hash saat
verifikasi berjalan normal (tanpa manipulasi setelah embedding).

Saat verifikasi, hash dihitung ulang dari MSB7 blok yang diterima. Perubahan
apa pun pada 7 bit teratas suatu piksel di dalam blok (cropping, penyuntingan,
override warna, kompresi ulang, dan lain-lain) membuat hash blok tidak cocok
lagi, sehingga blok tersebut ditandai "berubah". Verifikasi bersifat blind:
hanya butuh citra + secret key, tanpa citra asli.

Skema ini didesain untuk mendukung Bagian 3 Topik C pada dokumen tugas:
"Untuk jalur fragile, tampilkan peta area yang terdeteksi diubah." Bukan
pengganti tanda tangan digital bersertifikat; cukup untuk mendemonstrasikan
lokalisasi manipulasi pada watermark fragile tingkat mata kuliah.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Iterable, Optional

import numpy as np

TAMPER_BLOCK_SIZE = 16       # ukuran blok (piksel) untuk peta tamper
CHECK_BITS_PER_BLOCK = 16    # jumlah bit check per blok (dari HMAC-SHA256)


@dataclass
class TamperMap:
    rows: int
    cols: int
    block_size: int
    tampered: np.ndarray        # bool, shape (rows, cols)
    unverifiable: np.ndarray    # bool, shape (rows, cols) - blok tanpa piksel bebas
    tampered_blocks: int
    total_blocks: int
    tampered_ratio: float        # tampered_blocks / blok yang bisa diverifikasi


def _block_grid(shape, block_size: int):
    h, w = shape[0], shape[1]
    return h // block_size, w // block_size


def _block_flat_indices(row0: int, col0: int, block_size: int, width: int, channels: int) -> np.ndarray:
    """Indeks flat (untuk array hasil ``image.reshape(-1)``) satu blok, urutan tetap (baris, kolom, kanal)."""
    rows = np.arange(row0, row0 + block_size)
    cols = np.arange(col0, col0 + block_size)
    idx = (rows[:, None, None] * width + cols[None, :, None]) * channels + np.arange(channels)[None, None, :]
    return idx.reshape(-1).astype(np.int64)


def _check_bits(secret_key: str, block_index: int, msb7_bytes: bytes, n_bits: int) -> np.ndarray:
    key_bytes = secret_key.encode("utf-8")
    message = block_index.to_bytes(4, "big") + msb7_bytes
    digest = hmac.new(key_bytes, message, hashlib.sha256).digest()
    need_bytes = (n_bits + 7) // 8
    bits = np.unpackbits(np.frombuffer(digest[:need_bytes], dtype=np.uint8))
    return bits[:n_bits]


def _to_reserved_array(reserved_positions: Optional[Iterable[int]]) -> np.ndarray:
    """Normalize None / list / numpy array of reserved flat indices into a sorted int64 array."""
    if reserved_positions is None:
        return np.array([], dtype=np.int64)
    if isinstance(reserved_positions, np.ndarray) and reserved_positions.size == 0:
        return np.array([], dtype=np.int64)
    values = {int(p) for p in reserved_positions}
    return np.array(sorted(values), dtype=np.int64)


def _iter_blocks(shape, block_size: int, channels: int):
    bh, bw = _block_grid(shape, block_size)
    width = shape[1]
    block_index = 0
    for r in range(bh):
        for c in range(bw):
            positions = _block_flat_indices(r * block_size, c * block_size, block_size, width, channels)
            yield block_index, r, c, positions
            block_index += 1


def embed_tamper_watermark(
    image: np.ndarray,
    secret_key: str,
    reserved_positions: Optional[Iterable[int]] = None,
    block_size: int = TAMPER_BLOCK_SIZE,
) -> np.ndarray:
    """Kembalikan salinan ``image`` dengan bit autentikasi per-blok tertanam di LSB bebas."""
    if not secret_key:
        raise ValueError("Secret key tidak boleh kosong.")
    channels = image.shape[2] if image.ndim == 3 else 1
    reserved = _to_reserved_array(reserved_positions)
    flat = image.reshape(-1).copy()

    for block_index, _r, _c, positions in _iter_blocks(image.shape, block_size, channels):
        mask = ~np.isin(positions, reserved) if reserved.size else np.ones(positions.shape, dtype=bool)
        free = positions[mask]
        n_bits = min(CHECK_BITS_PER_BLOCK, free.size)
        if n_bits == 0:
            continue
        msb7 = (flat[positions] & 0xFE).astype(np.uint8).tobytes()
        bits = _check_bits(secret_key, block_index, msb7, n_bits)
        targets = free[:n_bits]
        flat[targets] = (flat[targets] & 0xFE) | bits
    return flat.reshape(image.shape)


def detect_tamper_map(
    image: np.ndarray,
    secret_key: str,
    reserved_positions: Optional[Iterable[int]] = None,
    block_size: int = TAMPER_BLOCK_SIZE,
) -> TamperMap:
    """Verifikasi tiap blok dan kembalikan peta area yang terdeteksi berubah."""
    if not secret_key:
        raise ValueError("Secret key tidak boleh kosong.")
    channels = image.shape[2] if image.ndim == 3 else 1
    bh, bw = _block_grid(image.shape, block_size)
    reserved = _to_reserved_array(reserved_positions)
    flat = image.reshape(-1)

    tampered = np.zeros((bh, bw), dtype=bool)
    unverifiable = np.zeros((bh, bw), dtype=bool)

    for block_index, r, c, positions in _iter_blocks(image.shape, block_size, channels):
        mask = ~np.isin(positions, reserved) if reserved.size else np.ones(positions.shape, dtype=bool)
        free = positions[mask]
        n_bits = min(CHECK_BITS_PER_BLOCK, free.size)
        if n_bits == 0:
            unverifiable[r, c] = True
            continue
        msb7 = (flat[positions] & 0xFE).astype(np.uint8).tobytes()
        expected = _check_bits(secret_key, block_index, msb7, n_bits)
        targets = free[:n_bits]
        actual = (flat[targets] & 1).astype(np.uint8)
        if not np.array_equal(expected, actual):
            tampered[r, c] = True

    total = bh * bw
    verifiable = total - int(unverifiable.sum())
    ratio = (int(tampered.sum()) / verifiable) if verifiable else 0.0
    return TamperMap(bh, bw, block_size, tampered, unverifiable, int(tampered.sum()), total, ratio)


def render_tamper_overlay(image: np.ndarray, tamper_map: TamperMap, alpha: float = 0.45) -> np.ndarray:
    """Gambarkan overlay merah tembus pandang di atas blok yang ditandai berubah."""
    overlay = image.copy()
    bs = tamper_map.block_size
    red = np.array([0, 0, 255], dtype=np.float32)  # BGR
    yellow = np.array([0, 200, 255], dtype=np.float32)
    for r in range(tamper_map.rows):
        for c in range(tamper_map.cols):
            if tamper_map.tampered[r, c]:
                color = red
            elif tamper_map.unverifiable[r, c]:
                color = yellow
            else:
                continue
            y0, y1 = r * bs, r * bs + bs
            x0, x1 = c * bs, c * bs + bs
            region = overlay[y0:y1, x0:x1].astype(np.float32)
            blended = region * (1 - alpha) + color * alpha
            overlay[y0:y1, x0:x1] = blended.astype(np.uint8)
    return overlay


def encode_png_data_uri(image: np.ndarray) -> str:
    """Encode a BGR image (numpy array) as a base64 PNG data: URI for inline <img>."""
    import base64

    import cv2

    ok, buf = cv2.imencode(".png", image)
    if not ok:  # pragma: no cover - defensive
        raise ValueError("Gagal meng-encode citra overlay ke PNG.")
    return "data:image/png;base64," + base64.b64encode(buf.tobytes()).decode("ascii")
