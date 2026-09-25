"""Synthetic test images (fallback dataset).

Dibuat dengan NumPy/OpenCV supaya proyek tidak membawa foto berhak cipta.
Tekstur multi-oktaf + grain membuat spektrum frekuensinya mirip foto asli.
Untuk pengujian final, gunakan foto nyata milikmu sendiri (lihat README).
"""

from __future__ import annotations

import cv2
import numpy as np

KINDS = ("landscape", "portrait", "object", "colorful", "document")


def _fractal(h: int, w: int, rng: np.random.Generator, octaves: int = 6, persistence: float = 0.55) -> np.ndarray:
    """Multi-octave value noise in range 0..1."""
    total = np.zeros((h, w), dtype=np.float32)
    amplitude, norm = 1.0, 0.0
    for octave in range(octaves):
        cells = 2 ** (octave + 2)
        grid = rng.random((cells, cells)).astype(np.float32)
        total += amplitude * cv2.resize(grid, (w, h), interpolation=cv2.INTER_CUBIC)
        norm += amplitude
        amplitude *= persistence
    total /= norm
    return np.clip((total - total.min()) / (np.ptp(total) + 1e-6), 0, 1)


def _finish(img: np.ndarray, rng: np.random.Generator, grain: float = 2.5) -> np.ndarray:
    noisy = img.astype(np.float32) + rng.normal(0, grain, img.shape).astype(np.float32)
    return np.clip(noisy, 0, 255).astype(np.uint8)


def _landscape(h: int, w: int, rng: np.random.Generator) -> np.ndarray:
    ys = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    sky = np.dstack([230 - 90 * ys, 190 - 70 * ys, 120 - 40 * ys]).repeat(w, axis=1)  # BGR
    profile = cv2.resize(rng.random((1, 12)).astype(np.float32), (w, 1), interpolation=cv2.INTER_CUBIC)[0]
    horizon = (h * (0.45 + 0.25 * profile)).astype(int)
    img = sky.copy()
    tex = _fractal(h, w, rng, 7)
    for x in range(w):
        y0 = horizon[x]
        shade = 0.5 + 0.5 * tex[y0:, x][:, None]
        ground = np.array([50, 110, 70], np.float32) * shade + np.array([20, 40, 30], np.float32)
        img[y0:, x] = ground
    return _finish(img, rng, 3.0)


def _portrait(h: int, w: int, rng: np.random.Generator) -> np.ndarray:
    bg = _fractal(h, w, rng, 5)
    img = np.dstack([90 + 70 * bg, 100 + 60 * bg, 120 + 50 * bg]).astype(np.float32)
    cx, cy = w // 2, int(h * 0.42)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    hair = ((xx - cx) / (w * 0.30)) ** 2 + ((yy - cy + h * 0.05) / (h * 0.30)) ** 2 < 1
    face = ((xx - cx) / (w * 0.22)) ** 2 + ((yy - cy) / (h * 0.27)) ** 2 < 1
    body = ((xx - cx) / (w * 0.45)) ** 2 + ((yy - h * 0.95) / (h * 0.30)) ** 2 < 1
    img[body] = (70, 60, 140)
    img[hair] = (25, 35, 55)
    shade = 0.75 + 0.25 * (1 - (xx - cx) / (w * 0.22)).clip(0, 2) / 2
    skin = np.dstack([140 * shade, 175 * shade, 220 * shade])
    img[face] = skin[face]
    for dx in (-0.09, 0.09):
        cv2.ellipse(img, (int(cx + dx * w), int(cy - h * 0.04)), (int(w * 0.03), int(h * 0.015)), 0, 0, 360, (40, 40, 40), -1)
    cv2.ellipse(img, (cx, int(cy + h * 0.12)), (int(w * 0.07), int(h * 0.03)), 0, 0, 180, (60, 60, 150), 3)
    return _finish(cv2.GaussianBlur(img, (0, 0), 1.2), rng, 3.0)


def _object(h: int, w: int, rng: np.random.Generator) -> np.ndarray:
    tex = _fractal(h, w, rng, 6)
    stripes = 0.5 + 0.5 * np.sin(np.linspace(0, 40, w, dtype=np.float32))[None, :] * tex
    img = np.dstack([60 + 50 * stripes, 100 + 60 * stripes, 150 + 60 * stripes]).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy, r = w * 0.4, h * 0.5, min(h, w) * 0.28
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    sphere = dist < r
    light = np.clip(1 - np.sqrt((xx - cx + r * 0.35) ** 2 + (yy - cy + r * 0.35) ** 2) / (r * 1.5), 0.1, 1)
    img[sphere] = (np.dstack([60 * light, 60 * light, 230 * light]))[sphere]
    x0, y0, x1, y1 = int(w * 0.62), int(h * 0.42), int(w * 0.9), int(h * 0.78)
    img[y0:y1, x0:x1] = np.array([200, 160, 60]) * (0.6 + 0.4 * tex[y0:y1, x0:x1, None])
    cv2.rectangle(img, (x0, y0), (x1, y1), (120, 90, 30), 2)
    return _finish(img, rng, 2.5)


def _colorful(h: int, w: int, rng: np.random.Generator) -> np.ndarray:
    base = _fractal(h, w, rng, 5)
    hue = (base * 179).astype(np.uint8)
    hsv = np.dstack([hue, np.full_like(hue, 200), np.full_like(hue, 230)])
    img = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR).astype(np.float32)
    for _ in range(14):
        center = (int(rng.integers(0, w)), int(rng.integers(0, h)))
        color = tuple(int(c) for c in rng.integers(30, 255, 3))
        if rng.random() < 0.5:
            cv2.circle(img, center, int(rng.integers(20, 70)), color, -1)
        else:
            p2 = (center[0] + int(rng.integers(30, 110)), center[1] + int(rng.integers(30, 110)))
            cv2.rectangle(img, center, p2, color, -1)
    return _finish(cv2.GaussianBlur(img, (0, 0), 0.8), rng, 3.0)


def _document(h: int, w: int, rng: np.random.Generator) -> np.ndarray:
    paper = 235 + 12 * _fractal(h, w, rng, 4)
    # OpenCV 5 mewajibkan citra 8-bit untuk cv2.putText, jadi kanvas dokumen dibuat uint8 sejak awal.
    img = np.clip(np.rint(np.dstack([paper * 0.96, paper * 0.98, paper])), 0, 255).astype(np.uint8)
    lines = ["LAPORAN KEAMANAN INFORMASI", "Digital Watermarking - Robust DCT", "Nomor Dokumen : DW-2024-001",
             "Watermark disisipkan pada domain frekuensi.", "PSNR, NC dan BER dihitung dari data aktual.",
             "Pengujian: JPEG, crop, resize, noise, brightness."]
    y = int(h * 0.12)
    for i, line in enumerate(lines):
        scale = 0.9 if i == 0 else 0.55
        cv2.putText(img, line, (int(w * 0.07), y), cv2.FONT_HERSHEY_SIMPLEX, scale * w / 512, (35, 35, 35), 1 + (i == 0), cv2.LINE_AA)
        y += int(h * 0.075)
    for row in range(4):
        cv2.line(img, (int(w * 0.07), y + row * 34), (int(w * 0.93), y + row * 34), (90, 90, 90), 1)
    for col in range(4):
        cv2.line(img, (int(w * (0.07 + 0.286 * col)), y), (int(w * (0.07 + 0.286 * col)), y + 102), (90, 90, 90), 1)
    for k in range(6):
        cv2.putText(img, f"data {k+1:02d}", (int(w * 0.09), y + 24 + (k % 3) * 34), cv2.FONT_HERSHEY_PLAIN, w / 500 * 1.1, (60, 60, 160), 1, cv2.LINE_AA)
    return _finish(img, rng, 2.0)


_BUILDERS = {"landscape": _landscape, "portrait": _portrait, "object": _object, "colorful": _colorful, "document": _document}


def make_synthetic_image(kind: str, width: int = 512, height: int = 512, seed: int = 0) -> np.ndarray:
    """Return a deterministic BGR uint8 test image of the requested kind."""
    if kind not in _BUILDERS:
        raise ValueError(f"Jenis citra tidak dikenal: {kind}")
    rng = np.random.default_rng(seed)
    return _BUILDERS[kind](height, width, rng)
