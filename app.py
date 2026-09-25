"""Flask application factory for Digital Watermarking - Robust DCT Image Protection.

Jalankan:  python app.py   ->   http://127.0.0.1:5001
"""

from __future__ import annotations

import logging
import os
import secrets
from typing import Optional

from flask import Flask, render_template
from werkzeug.exceptions import HTTPException

from routes.main_routes import main_bp
from routes.testing_routes import testing_bp
from routes.watermark_routes import wm_bp
from watermark import config
from watermark.service import Storage


def create_app(test_config: Optional[dict] = None) -> Flask:
    app = Flask(__name__)
    # SECRET_KEY hanya dipakai untuk session/flash. Diambil dari environment;
    # jika tidak ada, dibuat acak saat startup (tidak pernah ditulis di source code).
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_BYTES
    app.config["STORAGE"] = Storage.default()
    app.config["DATASET_DIR"] = config.DATASET_DIR
    if test_config:
        app.config.update(test_config)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config.ensure_directories()
    app.config["STORAGE"].ensure()

    app.register_blueprint(main_bp)
    app.register_blueprint(wm_bp)
    app.register_blueprint(testing_bp)

    @app.context_processor
    def inject_globals():
        return {"default_watermark": config.DEFAULT_WATERMARK_TEXT, "max_upload_mb": config.MAX_UPLOAD_BYTES // (1024 * 1024)}

    @app.errorhandler(Exception)
    def handle_error(error):
        """Friendly error pages. Tracebacks stay in the server log, never in the browser."""
        if isinstance(error, HTTPException):
            messages = {
                404: "Halaman atau file tidak ditemukan.",
                405: "Metode permintaan tidak diizinkan.",
                413: f"File terlalu besar. Maksimum {config.MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
            }
            message = messages.get(error.code, error.description)
            return render_template("error.html", code=error.code, message=message), error.code
        if app.debug:
            raise error
        app.logger.exception("Unhandled error")
        return render_template("error.html", code=500, message="Terjadi kesalahan pada server. Silakan coba lagi."), 500

    return app


app = create_app()

if __name__ == "__main__":
    # Debug (traceback di browser) hanya aktif jika FLASK_DEBUG=1.
    app.run(host="127.0.0.1", port=5001, debug=os.environ.get("FLASK_DEBUG") == "1")
