# flask-backend/app.py
from flask import Flask, Blueprint, send_from_directory, current_app
import logging

bp = Blueprint("web", __name__)

logger = logging.getLogger(__name__)


@bp.route("/")
def index():
    return send_from_directory(current_app.static_folder, "index.html")


@bp.route("/<path:path>")
def static_proxy(path):
    if "." in path:
        return send_from_directory(current_app.static_folder, path)
    else:
        return send_from_directory(current_app.static_folder, "index.html")
