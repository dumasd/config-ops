# flask-backend/app.py
from flask import Flask, Blueprint, render_template
import logging

bp = Blueprint("admin", __name__)

logger = logging.getLogger(__name__)


@bp.route("/", defaults={"path": ""})
@bp.route("/<path:path>")
def serve_vue(path):
    return render_template("index.html")
