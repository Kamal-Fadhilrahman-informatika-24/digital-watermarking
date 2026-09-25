"""Static pages: Home and About."""

from flask import Blueprint, render_template

from watermark import config

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    return render_template("index.html", pairs=config.COEFFICIENT_PAIRS)


@main_bp.route("/about")
def about():
    return render_template("about.html")
