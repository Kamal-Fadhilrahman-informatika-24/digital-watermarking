import numpy as np
from watermark.dct import blocks_dct, blocks_idct


def test_dct_roundtrip():
    x = np.random.default_rng(1).random((32, 48)) * 255
    assert np.allclose(blocks_idct(blocks_dct(x)), x)


def test_dct_preserves_energy():
    x = np.random.default_rng(2).random((16, 16)) * 255
    assert np.isclose(np.sum(blocks_dct(x) ** 2), np.sum(x ** 2))
