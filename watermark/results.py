"""Small result containers shared by the DCT and LSB methods."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple

import numpy as np

# (x0, y0, x1, y1) dalam piksel; area gambar yang benar-benar tersedia.
Region = Tuple[int, int, int, int]


@dataclass
class EmbedResult:
    image: np.ndarray  # BGR uint8
    method: str
    n_bits: int
    info: dict = field(default_factory=dict)


@dataclass
class ExtractionResult:
    valid: bool
    watermark: str
    message: str
    raw_bits: np.ndarray  # bit hasil baca mentah (header + body)
    header_valid: bool = False
    crc_valid: bool = False
    region: Optional[Region] = None
