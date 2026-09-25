"""Registry of available watermarking methods."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .dct_watermark import embed_dct_watermark, extract_dct_watermark
from .errors import WatermarkError
from .lsb_watermark import embed_lsb_watermark, extract_lsb_watermark


@dataclass(frozen=True)
class Method:
    key: str
    label: str
    robust: bool
    embed: Callable
    extract: Callable


METHODS = {
    "dct": Method("dct", "DCT Robust", True, embed_dct_watermark, extract_dct_watermark),
    "lsb": Method("lsb", "LSB Fragile", False, embed_lsb_watermark, extract_lsb_watermark),
}


def get_method(key: str) -> Method:
    """Return the method for ``key`` ('dct' or 'lsb') or raise a friendly error."""
    try:
        return METHODS[(key or "").lower()]
    except KeyError:
        raise WatermarkError("Metode tidak dikenal. Pilih DCT Robust atau LSB Fragile.") from None
