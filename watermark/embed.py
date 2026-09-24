"""Watermark robust: DCT blok 8x8 + spread spectrum pada koefisien frekuensi menengah.

Setiap bit watermark disebar ke banyak blok (dipilih acak dari kunci rahasia) dan dikali
barisan pseudo-noise (+1/-1). Deteksi memakai korelasi sehingga bersifat blind (tanpa citra asli).
"""
import hashlib
import numpy as np
from PIL import Image
from watermark.dct import blocks_dct, blocks_idct
from watermark.utils import text_to_bits

MID_POS = [(1, 3), (2, 2), (3, 1), (2, 3), (3, 2), (1, 4), (4, 1), (3, 3)]
ROWS = np.array([p[0] for p in MID_POS])
COLS = np.array([p[1] for p in MID_POS])
ALPHA = 12.0  # kekuatan watermark


def make_plan(secret_key, n_blocks, n_bits):
    """Urutan blok, pemilik bit tiap blok, dan barisan PN; semuanya ditentukan kunci rahasia."""
    seed = int.from_bytes(hashlib.sha256(str(secret_key).encode()).digest()[:8], 'big')
    rng = np.random.default_rng(seed)
    order = rng.permutation(n_blocks)
    pn = rng.choice([-1.0, 1.0], size=(n_blocks, len(MID_POS)))
    owner = np.arange(n_blocks) % n_bits
    return order, owner, pn


def pad8(channel):
    h, w = channel.shape
    return np.pad(channel, ((0, -h % 8), (0, -w % 8)), mode='edge')


def embed_watermark(image_path, watermark_text, secret_key, output_path, alpha=ALPHA):
    img = Image.open(image_path).convert('YCbCr')
    y_img, cb_img, cr_img = img.split()
    y = np.asarray(y_img, dtype=np.float64)
    h, w = y.shape

    coef = blocks_dct(pad8(y) - 128.0)
    hb, wb = coef.shape[:2]
    flat = coef.reshape(hb * wb, 8, 8)

    bits = np.array([int(b) for b in text_to_bits(watermark_text)])
    if len(bits) == 0 or len(bits) > hb * wb:
        raise ValueError('Teks watermark kosong atau terlalu panjang untuk ukuran citra ini.')

    order, owner, pn = make_plan(secret_key, hb * wb, len(bits))
    sign = np.where(bits[owner] == 1, 1.0, -1.0)
    flat[order[:, None], ROWS[None, :], COLS[None, :]] += alpha * sign[:, None] * pn

    y_new = blocks_idct(flat.reshape(hb, wb, 8, 8))[:h, :w] + 128.0
    y_new = Image.fromarray(np.clip(np.rint(y_new), 0, 255).astype(np.uint8))
    Image.merge('YCbCr', (y_new, cb_img, cr_img)).convert('RGB').save(output_path, 'PNG')
    return True
