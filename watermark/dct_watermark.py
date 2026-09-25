"""Robust, blind DCT watermarking on the luminance channel.

Pipeline embedding:
    BGR -> YCrCb -> Y channel -> blok 8x8 -> DCT (cv2.dct)
        -> urutan blok + pasangan koefisien ditentukan secret key
        -> atur selisih koefisien mid-frequency (bit 1 / bit 0)
        -> IDCT (cv2.idct) -> Y baru -> YCrCb -> BGR

Aturan embedding untuk satu blok dan satu pasangan koefisien (A, B):
    bit 1 : paksa  A - B >= +EMBED_STRENGTH
    bit 0 : paksa  A - B <= -EMBED_STRENGTH
Koefisien DC (0,0) tidak pernah diubah.

Extraction bersifat *blind*: hanya butuh citra + secret key (tanpa citra asli).
Setiap bit ditanam berulang di banyak blok yang tersebar acak (berdasarkan key)
lalu dibaca dengan soft voting, sehingga tahan terhadap kompresi/noise.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

import cv2
import numpy as np

from . import config
from .errors import CapacityError, PayloadError, WatermarkError
from .key_utils import generate_block_positions, generate_pair_indices
from .payload import (
    HEADER_BITS,
    body_bit_count,
    decode_body,
    encode_payload,
    parse_header,
)
from .results import EmbedResult, ExtractionResult, Region
from .utils import check_image as _check_image

logger = logging.getLogger(__name__)

BS = config.BLOCK_SIZE
_PAIRS = np.array(config.COEFFICIENT_PAIRS, dtype=np.int64)  # shape (P, 2, 2)


# --------------------------------------------------------------- helpers
def block_grid(shape: Tuple[int, ...]) -> Tuple[int, int]:
    """Number of full 8x8 blocks (rows, cols); border pixels are left untouched."""
    return shape[0] // BS, shape[1] // BS


def max_watermark_bytes(shape: Tuple[int, ...]) -> int:
    """Largest watermark (bytes) that still meets MIN_BODY_REPETITION."""
    bh, bw = block_grid(shape)
    free = bh * bw - config.HEADER_REPETITION * HEADER_BITS
    if free <= 0:
        return 0
    bits = free // config.MIN_BODY_REPETITION
    return max(0, min(config.MAX_WATERMARK_BYTES, bits // 8 - 4))


def _check_key(secret_key: str) -> None:
    if not secret_key:
        raise WatermarkError("Secret key tidak boleh kosong.")


def _luminance(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)[:, :, 0].astype(np.float32)


def _usable(block_ids: np.ndarray, bw: int, region: Optional[Region]) -> np.ndarray:
    """Boolean mask: block lies fully inside the valid region (all True if none)."""
    if region is None:
        return np.ones(len(block_ids), dtype=bool)
    x0, y0, x1, y1 = region
    by, bx = np.divmod(block_ids, bw)
    return (bx * BS >= x0) & ((bx + 1) * BS <= x1) & (by * BS >= y0) & ((by + 1) * BS <= y1)


def _block_differences(y: np.ndarray, block_ids: np.ndarray, bw: int, pair_ids: np.ndarray) -> np.ndarray:
    """DCT each requested block and return A - B of its key-selected coefficient pair."""
    diffs = np.zeros(len(block_ids), dtype=np.float64)
    for k, bid in enumerate(block_ids):
        by, bx = divmod(int(bid), bw)
        coeffs = cv2.dct(np.ascontiguousarray(y[by * BS:(by + 1) * BS, bx * BS:(bx + 1) * BS]))
        (ra, ca), (rb, cb) = _PAIRS[pair_ids[k]]
        diffs[k] = float(coeffs[ra, ca]) - float(coeffs[rb, cb])
    return diffs


def _soft_vote(diffs: np.ndarray, bit_index: np.ndarray, usable: np.ndarray, n_bits: int) -> np.ndarray:
    """Sum clipped differences per payload bit; positive sum -> bit 1."""
    clip = config.SOFT_VOTE_CLIP_FACTOR * config.EMBED_STRENGTH
    votes = np.zeros(n_bits, dtype=np.float64)
    np.add.at(votes, bit_index[usable], np.clip(diffs[usable], -clip, clip))
    return (votes > 0).astype(np.uint8)


def _layout(n_blocks: int, secret_key: str):
    order = np.array(generate_block_positions(n_blocks, secret_key), dtype=np.int64)
    pair_ids = generate_pair_indices(n_blocks, len(_PAIRS), secret_key)
    return order, pair_ids


def _body_blocks(order: np.ndarray, n_body_bits: int) -> Tuple[np.ndarray, int]:
    """Blocks used for the body and the repetition count per body bit."""
    h_blocks = config.HEADER_REPETITION * HEADER_BITS
    reps = (len(order) - h_blocks) // n_body_bits if len(order) > h_blocks else 0
    return order[h_blocks:h_blocks + reps * n_body_bits], reps


# --------------------------------------------------------------- embedding
def _embed_bit(coeffs: np.ndarray, pair: np.ndarray, bit: int, strength: float) -> None:
    (ra, ca), (rb, cb) = pair
    sign = 1.0 if bit else -1.0
    diff = float(coeffs[ra, ca]) - float(coeffs[rb, cb])
    if sign * diff < strength:  # hanya ubah bila belum memenuhi margin
        shift = (strength - sign * diff) / 2.0
        coeffs[ra, ca] += sign * shift
        coeffs[rb, cb] -= sign * shift


def embed_dct_watermark(
    image: np.ndarray, text: str, secret_key: str, strength: Optional[float] = None
) -> EmbedResult:
    """Embed ``text`` into ``image`` (BGR uint8) and return the watermarked image."""
    _check_key(secret_key)
    _check_image(image)
    strength = config.EMBED_STRENGTH if strength is None else float(strength)
    payload = encode_payload(text)

    bh, bw = block_grid(image.shape)
    n_blocks = bh * bw
    order, pair_ids = _layout(n_blocks, secret_key)
    n_body = len(payload.body_bits)
    body_blocks, reps = _body_blocks(order, n_body)
    if reps < config.MIN_BODY_REPETITION:
        raise CapacityError(
            "Watermark melebihi kapasitas citra ini. "
            f"Maksimum sekitar {max_watermark_bytes(image.shape)} byte untuk ukuran citra ini; "
            "gunakan teks lebih pendek atau citra lebih besar."
        )
    logger.info("DCT embedding started (blocks=%d, body_repetition=%d)", n_blocks, reps)

    ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
    y = ycrcb[:, :, 0].astype(np.float32)
    y_new = y.copy()

    h_blocks = config.HEADER_REPETITION * HEADER_BITS
    jobs = (
        (order[:h_blocks], payload.header_bits[np.arange(h_blocks) % HEADER_BITS]),
        (body_blocks, payload.body_bits[np.arange(len(body_blocks)) % n_body]),
    )
    for block_ids, bits in jobs:
        for bid, bit in zip(block_ids, bits):
            by, bx = divmod(int(bid), bw)
            window = (slice(by * BS, (by + 1) * BS), slice(bx * BS, (bx + 1) * BS))
            coeffs = cv2.dct(np.ascontiguousarray(y[window]))
            _embed_bit(coeffs, _PAIRS[pair_ids[bid]], int(bit), strength)
            y_new[window] = cv2.idct(coeffs)

    ycrcb[:, :, 0] = np.clip(np.rint(y_new), 0, 255).astype(np.uint8)
    watermarked = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)
    logger.info("DCT embedding completed")
    return EmbedResult(
        image=watermarked,
        method="dct",
        n_bits=len(payload.all_bits),
        info={
            "blocks_total": n_blocks,
            "header_blocks": h_blocks,
            "body_repetition": reps,
            "strength": strength,
            "block_size": BS,
        },
    )


# -------------------------------------------------------------- extraction
def _read_body(y, order, pair_ids, bw, length, region) -> np.ndarray:
    n_body = body_bit_count(length)
    body_blocks, reps = _body_blocks(order, n_body)
    if reps < 1:
        raise PayloadError("Payload watermark tidak muat pada citra ini (ukuran citra berbeda?).")
    diffs = _block_differences(y, body_blocks, bw, pair_ids[body_blocks])
    return _soft_vote(diffs, np.arange(len(body_blocks)) % n_body, _usable(body_blocks, bw, region), n_body)


def extract_dct_watermark(
    image: np.ndarray,
    secret_key: str,
    valid_region: Optional[Region] = None,
    force_length: Optional[int] = None,
) -> ExtractionResult:
    """Blind extraction.

    ``valid_region``  : area piksel yang sah (dipakai setelah serangan cropping).
    ``force_length``  : panjang watermark (byte) yang sudah diketahui; hanya dipakai
                        pengujian agar NC/BER tetap dapat dihitung walau header rusak.
                        Status valid/invalid tetap ditentukan oleh header + CRC asli.
    """
    _check_key(secret_key)
    _check_image(image)
    y = _luminance(image)
    bh, bw = block_grid(image.shape)
    n_blocks = bh * bw
    order, pair_ids = _layout(n_blocks, secret_key)

    h_blocks = config.HEADER_REPETITION * HEADER_BITS
    if n_blocks <= h_blocks:
        return ExtractionResult(False, "", "Citra terlalu kecil untuk memuat payload watermark.",
                                np.zeros(HEADER_BITS, np.uint8), region=valid_region)
    header_ids = order[:h_blocks]
    diffs = _block_differences(y, header_ids, bw, pair_ids[header_ids])
    header_bits = _soft_vote(diffs, np.arange(h_blocks) % HEADER_BITS, _usable(header_ids, bw, valid_region), HEADER_BITS)

    try:
        length = parse_header(header_bits)
        header_ok = True
        message = ""
    except PayloadError as exc:
        header_ok, length, message = False, force_length, str(exc)

    if length is None:  # header rusak dan panjang tidak diketahui
        return ExtractionResult(False, "", message, header_bits, region=valid_region)

    try:
        body_bits = _read_body(y, order, pair_ids, bw, length, valid_region)
    except PayloadError as exc:
        return ExtractionResult(False, "", message or str(exc), header_bits, header_ok, False, valid_region)

    raw = np.concatenate([header_bits, body_bits])
    if not header_ok:
        return ExtractionResult(False, "", message, raw, False, False, valid_region)
    try:
        text = decode_body(body_bits, length)
    except PayloadError as exc:
        return ExtractionResult(False, "", str(exc), raw, True, False, valid_region)
    logger.info("DCT extraction completed (valid)")
    return ExtractionResult(True, text, "Watermark berhasil dideteksi.", raw, True, True, valid_region)
