"""Structured watermark payload.

Layout (semua big-endian):

    HEADER : MAGIC "DW01" (4 byte) | VERSION (1 byte) | LENGTH (1 byte)   = 48 bit
    BODY   : watermark UTF-8 (LENGTH byte) | CRC32 dari watermark (4 byte)

Header memberi tahu extractor kapan harus berhenti membaca. CRC32 memastikan
teks yang keluar benar-benar sama dengan yang disisipkan.
"""

from __future__ import annotations

import zlib
from dataclasses import dataclass

import numpy as np

from . import config
from .errors import PayloadError, WatermarkError

HEADER_BYTES = len(config.PAYLOAD_MAGIC) + 2
HEADER_BITS = HEADER_BYTES * 8
CRC_BYTES = 4


@dataclass(frozen=True)
class EncodedPayload:
    text: str
    data_length: int  # jumlah byte UTF-8 watermark
    header_bits: np.ndarray
    body_bits: np.ndarray

    @property
    def all_bits(self) -> np.ndarray:
        return np.concatenate([self.header_bits, self.body_bits])


def bytes_to_bits(data: bytes) -> np.ndarray:
    """bytes -> array of bits (uint8 0/1), MSB first."""
    return np.unpackbits(np.frombuffer(data, dtype=np.uint8))


def bits_to_bytes(bits: np.ndarray) -> bytes:
    """array of bits -> bytes. Length must be a multiple of 8."""
    bits = np.asarray(bits, dtype=np.uint8)
    if bits.size % 8 != 0:
        raise ValueError("Jumlah bit harus kelipatan 8.")
    return np.packbits(bits).tobytes()


def body_bit_count(data_length: int) -> int:
    return (data_length + CRC_BYTES) * 8


def encode_payload(text: str) -> EncodedPayload:
    """Validate the watermark text and build header + body bits."""
    if text is None or text.strip() == "":
        raise WatermarkError("Teks watermark tidak boleh kosong.")
    data = text.encode("utf-8")
    if len(data) > config.MAX_WATERMARK_BYTES:
        raise WatermarkError(
            f"Watermark terlalu panjang ({len(data)} byte). "
            f"Maksimum {config.MAX_WATERMARK_BYTES} byte (UTF-8)."
        )
    header = config.PAYLOAD_MAGIC + bytes([config.PAYLOAD_VERSION, len(data)])
    crc = zlib.crc32(data).to_bytes(CRC_BYTES, "big")
    return EncodedPayload(
        text=text,
        data_length=len(data),
        header_bits=bytes_to_bits(header),
        body_bits=bytes_to_bits(data + crc),
    )


def parse_header(header_bits: np.ndarray) -> int:
    """Return the data length announced by the header, or raise PayloadError."""
    header = bits_to_bytes(header_bits)
    magic = header[: len(config.PAYLOAD_MAGIC)]
    if magic != config.PAYLOAD_MAGIC:
        raise PayloadError(
            "Payload watermark tidak ditemukan. "
            "Watermark tidak valid atau secret key salah."
        )
    version, length = header[-2], header[-1]
    if version != config.PAYLOAD_VERSION:
        raise PayloadError("Versi payload watermark tidak dikenali.")
    if length == 0 or length > config.MAX_WATERMARK_BYTES:
        raise PayloadError("Panjang payload watermark tidak valid.")
    return int(length)


def decode_body(body_bits: np.ndarray, data_length: int) -> str:
    """Verify CRC32 and return the watermark text."""
    raw = bits_to_bytes(body_bits)
    data, crc = raw[:data_length], raw[data_length : data_length + CRC_BYTES]
    if zlib.crc32(data).to_bytes(CRC_BYTES, "big") != crc:
        raise PayloadError(
            "Payload terdeteksi tetapi datanya rusak (CRC tidak cocok). "
            "Citra kemungkinan telah dimanipulasi."
        )
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:  # pragma: no cover - CRC normally catches this
        raise PayloadError("Data watermark bukan teks UTF-8 yang valid.") from exc
