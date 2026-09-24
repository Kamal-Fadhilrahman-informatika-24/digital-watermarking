"""Deteksi/ekstraksi watermark (blind) dengan korelasi terhadap barisan PN dari kunci rahasia."""
import numpy as np
from PIL import Image
from watermark.dct import blocks_dct
from watermark.embed import make_plan, pad8, ROWS, COLS
from watermark.utils import bits_to_text


def extract_watermark(watermarked_image_path, secret_key, watermark_length_bytes=8):
    y = np.asarray(Image.open(watermarked_image_path).convert('YCbCr').split()[0], dtype=np.float64)
    coef = blocks_dct(pad8(y) - 128.0)
    hb, wb = coef.shape[:2]
    flat = coef.reshape(hb * wb, 8, 8)

    n_bits = watermark_length_bytes * 8
    order, owner, pn = make_plan(secret_key, hb * wb, n_bits)
    vals = flat[order[:, None], ROWS[None, :], COLS[None, :]]
    corr = (vals * pn).sum(axis=1)
    score = np.bincount(owner, weights=corr, minlength=n_bits)

    bits = ''.join('1' if s > 0 else '0' for s in score)
    return bits_to_text(bits), bits
