# flask-backend/app.py
from flask import Flask, Blueprint, send_from_directory
import logging, os

bp = Blueprint("web", __name__)

logger = logging.getLogger(__name__)


@bp.route("/")
def index():
    return send_from_directory("static", "index.html")


@bp.route("/<path:path>")
def static_proxy(path):
    if "." in path:
        return send_from_directory("static", path)
    else:
        return send_from_directory("static", "index.html")
