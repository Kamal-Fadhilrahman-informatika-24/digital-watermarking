"""Secret-key handling.

Alur:  secret key -> SHA-256 -> seed (integer) -> random.Random(seed)
       -> urutan blok / pasangan koefisien / posisi LSB.

Key yang sama selalu menghasilkan urutan yang sama, key berbeda menghasilkan
urutan yang berbeda. Key tidak pernah disimpan atau dicatat di log.
"""

from __future__ import annotations

import hashlib
import random
from typing import List

import numpy as np


def derive_seed(secret_key: str, context: str = "") -> int:
    """Turn a secret key into a 256-bit integer seed using SHA-256.

    ``context`` memisahkan seed untuk keperluan berbeda (blok, pasangan, LSB)
    sehingga satu key menghasilkan beberapa aliran acak yang independen.
    """
    if not isinstance(secret_key, str) or secret_key == "":
        raise ValueError("Secret key tidak boleh kosong.")
    material = f"digital-watermarking|{context}|{secret_key}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest(), "big")


def generate_block_positions(n_blocks: int, secret_key: str) -> List[int]:
    """Return a key-dependent permutation of ``range(n_blocks)``."""
    if n_blocks <= 0:
        raise ValueError("n_blocks harus positif.")
    rng = random.Random(derive_seed(secret_key, "dct-block-order"))
    order = list(range(n_blocks))
    rng.shuffle(order)
    return order


def generate_pair_indices(n_blocks: int, n_pairs: int, secret_key: str) -> np.ndarray:
    """Choose, per block, which coefficient pair carries the bit (key-dependent)."""
    rng = random.Random(derive_seed(secret_key, "dct-coefficient-pair"))
    return np.array([rng.randrange(n_pairs) for _ in range(n_blocks)], dtype=np.int64)


def generate_lsb_positions(total_positions: int, count: int, secret_key: str) -> List[int]:
    """Key-dependent distinct positions for LSB embedding.

    Urutan bersifat *prefix-consistent*: posisi ke-k selalu sama berapa pun
    ``count``-nya. Ini memungkinkan header dibaca lebih dulu, lalu body.
    """
    if count > total_positions:
        raise ValueError("Jumlah posisi melebihi kapasitas.")
    rng = random.Random(derive_seed(secret_key, "lsb-positions"))
    chosen: List[int] = []
    used = set()
    while len(chosen) < count:
        pos = rng.randrange(total_positions)
        if pos not in used:
            used.add(pos)
            chosen.append(pos)
    return chosen
