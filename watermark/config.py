"""Central configuration.

Semua parameter penting (kekuatan embedding, pasangan koefisien DCT, parameter
serangan, batas upload) ada di file ini supaya mudah diubah dan dijelaskan.
Tidak ada secret key / password di file ini.
"""

from __future__ import annotations

from pathlib import Path

# ----------------------------------------------------------------- folders
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
WATERMARKED_DIR = OUTPUT_DIR / "watermarked"
ATTACK_DIR = OUTPUT_DIR / "attacks"
EXTRACTED_DIR = OUTPUT_DIR / "extracted"
CHART_DIR = OUTPUT_DIR / "charts"
REPORT_DIR = OUTPUT_DIR / "reports"
TEST_DATA_DIR = BASE_DIR / "test_data"
DATASET_DIR = TEST_DATA_DIR / "original"

REPORT_XLSX_NAME = "watermark_testing.xlsx"
LAST_EVALUATION_JSON = "last_evaluation.json"

# ------------------------------------------------------------ upload rules
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB
MIN_IMAGE_SIDE = 128  # pixel (sisi terpendek)
MAX_PROCESS_SIDE = 1024  # gambar lebih besar di-resize (rasio tetap) sebelum diproses
TEMP_FILE_MAX_AGE_HOURS = 24

# ------------------------------------------------------------ payload rules
PAYLOAD_MAGIC = b"DW01"  # penanda payload watermark
PAYLOAD_VERSION = 1
MAX_WATERMARK_BYTES = 64  # panjang watermark maksimum (bytes UTF-8)
DEFAULT_WATERMARK_TEXT = "KAMAL FADHILRAHMAN"

# ------------------------------------------------------------- DCT method
BLOCK_SIZE = 8

# Pasangan koefisien mid-frequency (baris, kolom) pada blok DCT 8x8.
# Koefisien (0,0) = DC TIDAK dipakai. Setiap blok memilih satu pasangan
# secara deterministik dari secret key.
# Bit 1  -> koefisien A - koefisien B >= +EMBED_STRENGTH
# Bit 0  -> koefisien A - koefisien B <= -EMBED_STRENGTH
COEFFICIENT_PAIRS = [
    ((2, 3), (3, 2)),
    ((1, 4), (4, 1)),
    ((2, 4), (4, 2)),
]

# Margin (dalam satuan koefisien DCT ortonormal). Makin besar -> makin tahan
# serangan, tetapi PSNR makin turun. Dokumentasi: docs/algorithm.md
EMBED_STRENGTH = 24.0

# Header dipakai untuk membaca panjang payload, jadi ditanam berulang
# (HEADER_REPETITION blok per bit header). Body payload memakai sisa blok.
HEADER_REPETITION = 16
MIN_BODY_REPETITION = 5  # minimal pengulangan per bit body agar dianggap muat
SOFT_VOTE_CLIP_FACTOR = 3.0  # selisih koefisien di-clip ke +/- (faktor * strength)

# Jika PSNR (asli vs watermarked) di bawah nilai ini, tampilkan peringatan.
# Nilai ini hanya memicu pesan; angka PSNR tetap angka hasil perhitungan.
PSNR_WARNING_DB = 30.0

# ------------------------------------------------------ attack parameters
JPEG_QUALITIES = (90, 70, 50)
CROP_RATIO = 0.10  # 10% lebar & tinggi dipotong (5% dari tiap sisi)
RESIZE_SCALE = 0.75  # 75% dari ukuran asli
NOISE_SIGMA = 5.0  # simpangan baku Gaussian noise (skala piksel 0-255)
NOISE_SEED = 2024  # seed tetap agar hasil pengujian bisa direproduksi
BRIGHTNESS_DELTA = 20  # +20 pada setiap channel
CONTRAST_FACTOR = 1.2  # +20% kontras (terhadap nilai tengah 128)

# ----------------------------------------------------------------- dataset
DATASET_IMAGE_NAMES = [f"image0{i}.png" for i in range(1, 6)]


def ensure_directories() -> None:
    """Create all runtime folders if they do not exist yet."""
    for folder in (
        UPLOAD_DIR,
        WATERMARKED_DIR,
        ATTACK_DIR,
        EXTRACTED_DIR,
        CHART_DIR,
        REPORT_DIR,
        DATASET_DIR,
    ):
        folder.mkdir(parents=True, exist_ok=True)
