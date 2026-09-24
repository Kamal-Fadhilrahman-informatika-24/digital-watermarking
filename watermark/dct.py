"""DCT 2D orthonormal per blok 8x8, ditulis sendiri dengan NumPy (tanpa scipy/cv2)."""
import numpy as np


def _dct_matrix(n=8):
    k = np.arange(n).reshape(-1, 1)
    i = np.arange(n).reshape(1, -1)
    m = np.cos(np.pi * (2 * i + 1) * k / (2 * n)) * np.sqrt(2.0 / n)
    m[0, :] = np.sqrt(1.0 / n)
    return m


D = _dct_matrix(8)


def blocks_dct(channel):
    """Kanal HxW (H, W kelipatan 8) -> koefisien berbentuk (H/8, W/8, 8, 8)."""
    h, w = channel.shape
    blocks = channel.reshape(h // 8, 8, w // 8, 8).transpose(0, 2, 1, 3)
    return D @ blocks @ D.T


def blocks_idct(coef):
    """Kebalikan blocks_dct: (H/8, W/8, 8, 8) -> kanal HxW."""
    blocks = D.T @ coef @ D
    hb, wb = blocks.shape[:2]
    return blocks.transpose(0, 2, 1, 3).reshape(hb * 8, wb * 8)
