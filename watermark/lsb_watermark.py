"""LSB *fragile* watermarking (fitur pengayaan).

Setiap bit payload (header + body, format sama dengan metode DCT) ditulis ke
bit paling tidak signifikan (LSB) dari sebuah nilai piksel-channel. Posisi
ditentukan secret key (SHA-256 -> seed -> PRNG), tanpa pengulangan.

Metode ini SENGAJA rapuh: hampir semua manipulasi (JPEG, noise, contrast, ...)
mengubah LSB sehingga watermark hilang. Ia dipakai sebagai pembanding untuk
DCT yang robust - bukan sebagai metode yang tahan serangan.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

from .errors import CapacityError, PayloadError, WatermarkError
from .key_utils import generate_lsb_positions
from .payload import HEADER_BITS, body_bit_count, decode_body, encode_payload, parse_header
from .results import EmbedResult, ExtractionResult, Region
from .utils import check_image

logger = logging.getLogger(__name__)


def embed_lsb_watermark(image: np.ndarray, text: str, secret_key: str) -> EmbedResult:
    """Write the payload into key-selected LSBs of the BGR pixel values."""
    if not secret_key:
        raise WatermarkError("Secret key tidak boleh kosong.")
    check_image(image)
    payload = encode_payload(text)
    bits = payload.all_bits
    total = image.size
    if len(bits) > total:
        raise CapacityError("Watermark melebihi kapasitas citra ini.")
    logger.info("LSB embedding started")
    positions = np.array(generate_lsb_positions(total, len(bits), secret_key), dtype=np.int64)
    flat = image.reshape(-1).copy()
    flat[positions] = (flat[positions] & 0xFE) | bits
    logger.info("LSB embedding completed")
    return EmbedResult(flat.reshape(image.shape), "lsb", len(bits), {"capacity_bits": int(total)})


def _read_bits(flat: np.ndarray, width: int, positions: np.ndarray, region: Optional[Region]) -> np.ndarray:
    bits = (flat[positions] & 1).astype(np.uint8)
    if region is not None:  # posisi di area yang hilang (crop) -> erasure, dianggap 0
        x0, y0, x1, y1 = region
        rows = positions // (width * 3)
        cols = (positions % (width * 3)) // 3
        outside = (cols < x0) | (cols >= x1) | (rows < y0) | (rows >= y1)
        bits[outside] = 0
    return bits


def extract_lsb_watermark(
    image: np.ndarray,
    secret_key: str,
    valid_region: Optional[Region] = None,
    force_length: Optional[int] = None,
) -> ExtractionResult:
    """Read the LSB payload back. Parameters follow ``extract_dct_watermark``."""
    if not secret_key:
        raise WatermarkError("Secret key tidak boleh kosong.")
    check_image(image)
    flat = image.reshape(-1)
    width = image.shape[1]
    header_pos = np.array(generate_lsb_positions(flat.size, HEADER_BITS, secret_key), dtype=np.int64)
    header_bits = _read_bits(flat, width, header_pos, valid_region)
    try:
        length, header_ok, message = parse_header(header_bits), True, ""
    except PayloadError as exc:
        length, header_ok, message = force_length, False, str(exc)
    if length is None:
        return ExtractionResult(False, "", message, header_bits, region=valid_region)

    total_bits = HEADER_BITS + body_bit_count(length)
    if total_bits > flat.size:
        return ExtractionResult(False, "", message or "Payload tidak muat pada citra ini.", header_bits, header_ok, False, valid_region)
    positions = np.array(generate_lsb_positions(flat.size, total_bits, secret_key), dtype=np.int64)
    bits = _read_bits(flat, width, positions, valid_region)
    raw, body = bits, bits[HEADER_BITS:]
    if not header_ok:
        return ExtractionResult(False, "", message, raw, False, False, valid_region)
    try:
        text = decode_body(body, length)
    except PayloadError as exc:
        return ExtractionResult(False, "", str(exc), raw, True, False, valid_region)
    logger.info("LSB extraction completed (valid)")
    return ExtractionResult(True, text, "Watermark berhasil dideteksi.", raw, True, True, valid_region)
