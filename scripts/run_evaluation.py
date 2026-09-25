"""Automated evaluation on the whole dataset (DCT Robust vs LSB Fragile).

Pemakaian:
    python scripts/run_evaluation.py
    python scripts/run_evaluation.py --watermark "KAMAL FADHILRAHMAN"

Secret key TIDAK ditulis di source code. Urutan sumber key:
    1. variabel lingkungan WATERMARK_SECRET_KEY
    2. opsi --key (hati-hati: tersimpan di riwayat terminal)
    3. prompt tersembunyi (getpass) - paling aman

Output:
    outputs/reports/watermark_testing.xlsx
    outputs/reports/watermark_testing.csv
    outputs/reports/last_evaluation.json
    outputs/charts/*.png
"""

import argparse
import csv
import getpass
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from watermark import config  # noqa: E402
from watermark.errors import WatermarkError  # noqa: E402
from watermark.evaluation import (  # noqa: E402
    evaluate_dataset,
    generate_synthetic_dataset,
    list_dataset_images,
    save_results_json,
)
from watermark.report import RESULT_COLUMNS, make_charts, summarize, write_xlsx  # noqa: E402


def read_secret_key(cli_value: str) -> str:
    key = os.environ.get("WATERMARK_SECRET_KEY") or cli_value
    if not key:
        if not sys.stdin.isatty():
            raise SystemExit("Secret key kosong. Set WATERMARK_SECRET_KEY atau jalankan di terminal interaktif.")
        key = getpass.getpass("Masukkan secret key (tidak ditampilkan): ")
    if not key:
        raise SystemExit("Secret key tidak boleh kosong.")
    return key


def write_csv(rows, path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(RESULT_COLUMNS)
        for r in rows:
            writer.writerow([r["image"], r["method"], r["attack"], r["parameter"], f"{r['psnr_watermarked']:.4f}",
                             f"{r['psnr_after_attack']:.4f}", f"{r['nc']:.6f}", f"{r['ber']:.6f}",
                             r["extracted_watermark"], r["status"]])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--watermark", default=config.DEFAULT_WATERMARK_TEXT, help="teks watermark")
    parser.add_argument("--key", default="", help="secret key (lebih aman lewat env/prompt)")
    parser.add_argument("--dataset", default=str(config.DATASET_DIR), help="folder citra asli")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    config.ensure_directories()
    dataset_dir = Path(args.dataset)
    if not list_dataset_images(dataset_dir):
        print("Dataset kosong -> membuat dataset sintetis...")
        generate_synthetic_dataset(dataset_dir)
    key = read_secret_key(args.key)

    def progress(message: str) -> None:
        print(f"  {message}", flush=True)

    print(f"Menjalankan evaluasi pada {len(list_dataset_images(dataset_dir))} citra...")
    try:
        results = evaluate_dataset(dataset_dir, key, args.watermark, progress=progress)
    except WatermarkError as exc:
        raise SystemExit(f"Error: {exc}")

    xlsx = write_xlsx(results, config.REPORT_DIR / config.REPORT_XLSX_NAME)
    write_csv(results["rows"], config.REPORT_DIR / "watermark_testing.csv")
    save_results_json(results, config.REPORT_DIR / config.LAST_EVALUATION_JSON)
    charts = make_charts(results["rows"], config.CHART_DIR)

    print("\nRingkasan (rata-rata seluruh citra)")
    print(f"{'Method':<12}{'Attack':<24}{'PSNR atk':>9}{'NC':>8}{'BER':>8}  Success")
    for s in summarize(results["rows"]):
        psnr = "inf" if s["mean_psnr"] == float("inf") else f"{s['mean_psnr']:.2f}"
        print(f"{s['method']:<12}{s['short']:<24}{psnr:>9}{s['mean_nc']:>8.4f}{s['mean_ber']:>8.4f}  {s['success']}/{s['n']}")
    print(f"\nXLSX   : {xlsx.relative_to(config.BASE_DIR)}")
    print(f"Grafik : {', '.join('outputs/charts/' + name for name in charts.values())}")
    print(f"Waktu  : {results['seconds']} detik")


if __name__ == "__main__":
    main()
