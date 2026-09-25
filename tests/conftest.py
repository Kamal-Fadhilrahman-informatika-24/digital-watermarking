"""Fixture bersama untuk semua pengujian.

Secret key di bawah ini adalah kunci UJI (dummy), bukan secret asli aplikasi.
Semua citra uji dibuat secara deterministik oleh watermark/synthetic.py.
"""

from __future__ import annotations

import io

import cv2
import numpy as np
import pytest

from watermark.service import Storage
from watermark.synthetic import make_synthetic_image

TEST_KEY = "kunci-uji-pytest-A"
OTHER_KEY = "kunci-uji-pytest-B"
TEST_TEXT = "KAMAL FADHILRAHMAN"


@pytest.fixture(scope="session")
def key() -> str:
    return TEST_KEY


@pytest.fixture(scope="session")
def other_key() -> str:
    return OTHER_KEY


@pytest.fixture(scope="session")
def text() -> str:
    return TEST_TEXT


@pytest.fixture(scope="session")
def cover() -> np.ndarray:
    """Citra uji 512x512 (BGR uint8), tidak pernah diubah oleh test."""
    image = make_synthetic_image("landscape", 512, 512, seed=0)
    image.setflags(write=False)
    return image


@pytest.fixture()
def cover_copy(cover) -> np.ndarray:
    return cover.copy()


def png_bytes(image: np.ndarray) -> bytes:
    ok, buffer = cv2.imencode(".png", image)
    assert ok
    return buffer.tobytes()


@pytest.fixture(scope="session")
def cover_png(cover) -> bytes:
    return png_bytes(cover)


@pytest.fixture()
def storage(tmp_path) -> Storage:
    store = Storage(
        upload=tmp_path / "uploads",
        watermarked=tmp_path / "watermarked",
        attacks=tmp_path / "attacks",
        extracted=tmp_path / "extracted",
        charts=tmp_path / "charts",
        reports=tmp_path / "reports",
    )
    store.ensure()
    return store


@pytest.fixture()
def app(tmp_path, storage):
    from app import create_app

    dataset = tmp_path / "dataset"
    dataset.mkdir()
    application = create_app({"TESTING": True, "STORAGE": storage, "DATASET_DIR": dataset})
    return application


@pytest.fixture()
def client(app):
    return app.test_client()


def upload(client, url: str, image_bytes: bytes, filename: str = "foto.png", **fields):
    """POST multipart dengan satu file gambar + field form."""
    data = {"image": (io.BytesIO(image_bytes), filename)}
    data.update(fields)
    return client.post(url, data=data, content_type="multipart/form-data")
