"""Generate the 5-image synthetic fallback dataset into test_data/original/.

Pemakaian:
    python scripts/generate_test_dataset.py            # buat yang belum ada
    python scripts/generate_test_dataset.py --force    # timpa semua

Untuk pengujian final, ganti/tambahkan minimal 5 foto nyata milikmu sendiri
(landscape, portrait, objek, berwarna, dokumen) di test_data/original/.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from watermark import config  # noqa: E402
from watermark.evaluation import generate_synthetic_dataset  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--force", action="store_true", help="timpa file yang sudah ada")
    parser.add_argument("--size", type=int, default=512, help="sisi citra (piksel), default 512")
    args = parser.parse_args()
    written = generate_synthetic_dataset(config.DATASET_DIR, args.size, overwrite=args.force)
    if written:
        for path in written:
            print(f"dibuat : {path.relative_to(config.BASE_DIR)}")
    else:
        print("Semua citra dataset sudah ada (pakai --force untuk menimpa).")


if __name__ == "__main__":
    main()
