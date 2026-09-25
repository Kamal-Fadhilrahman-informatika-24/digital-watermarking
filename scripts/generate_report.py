"""Rebuild the XLSX report and charts from the last saved evaluation.

Pemakaian (setelah python scripts/run_evaluation.py atau tombol Comparison di web):
    python scripts/generate_report.py

Tidak menjalankan ulang pengujian dan tidak membutuhkan secret key.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from watermark import config  # noqa: E402
from watermark.evaluation import load_results_json  # noqa: E402
from watermark.report import make_charts, write_xlsx  # noqa: E402


def main() -> None:
    config.ensure_directories()
    results = load_results_json(config.REPORT_DIR / config.LAST_EVALUATION_JSON)
    if results is None:
        raise SystemExit("Belum ada hasil evaluasi. Jalankan dulu: python scripts/run_evaluation.py")
    xlsx = write_xlsx(results, config.REPORT_DIR / config.REPORT_XLSX_NAME)
    charts = make_charts(results["rows"], config.CHART_DIR)
    print(f"XLSX   : {xlsx.relative_to(config.BASE_DIR)}")
    print(f"Grafik : {', '.join(charts.values())}")


if __name__ == "__main__":
    main()
