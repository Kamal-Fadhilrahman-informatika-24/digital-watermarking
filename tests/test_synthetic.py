"""Pengujian pembuat citra sintetis (dataset cadangan)."""

import numpy as np
import pytest

from watermark.synthetic import KINDS, make_synthetic_image


@pytest.mark.parametrize("kind", KINDS)
def test_every_kind_builds_a_valid_uint8_image(kind):
    image = make_synthetic_image(kind, 256, 192, seed=1)
    assert image.shape == (192, 256, 3) and image.dtype == np.uint8
    assert image.std() > 5, "citra tidak boleh datar"


@pytest.mark.parametrize("kind", KINDS)
def test_images_are_deterministic_per_seed(kind):
    a = make_synthetic_image(kind, 128, 128, seed=3)
    assert np.array_equal(a, make_synthetic_image(kind, 128, 128, seed=3))
    assert not np.array_equal(a, make_synthetic_image(kind, 128, 128, seed=4))


def test_unknown_kind_is_rejected():
    with pytest.raises(ValueError):
        make_synthetic_image("tidak-ada")
