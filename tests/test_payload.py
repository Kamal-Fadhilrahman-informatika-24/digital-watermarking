"""Pengujian format payload (header + CRC32)."""

import numpy as np
import pytest

from watermark import config
from watermark.errors import PayloadError, WatermarkError
from watermark.payload import (
    HEADER_BITS,
    bits_to_bytes,
    bytes_to_bits,
    decode_body,
    encode_payload,
    parse_header,
)


def test_bits_bytes_roundtrip():
    data = bytes(range(0, 256, 7))
    assert bits_to_bytes(bytes_to_bits(data)) == data


def test_payload_roundtrip_ascii_and_unicode():
    for text in ("KAMAL FADHILRAHMAN", "Universitas Indonesia - Keamanan Informasi", "Aé日本"):
        payload = encode_payload(text)
        assert parse_header(payload.header_bits) == len(text.encode("utf-8"))
        assert decode_body(payload.body_bits, payload.data_length) == text


def test_header_has_expected_size_and_magic():
    payload = encode_payload("abc")
    assert len(payload.header_bits) == HEADER_BITS == 48
    assert bits_to_bytes(payload.header_bits)[:4] == config.PAYLOAD_MAGIC


def test_corrupted_header_is_rejected():
    payload = encode_payload("abc")
    bad = payload.header_bits.copy()
    bad[3] ^= 1
    with pytest.raises(PayloadError):
        parse_header(bad)


def test_crc_detects_a_single_flipped_bit():
    payload = encode_payload("KAMAL")
    body = payload.body_bits.copy()
    body[5] ^= 1
    with pytest.raises(PayloadError):
        decode_body(body, payload.data_length)


def test_empty_and_too_long_watermark_are_rejected():
    with pytest.raises(WatermarkError):
        encode_payload("   ")
    with pytest.raises(WatermarkError):
        encode_payload("x" * (config.MAX_WATERMARK_BYTES + 1))
