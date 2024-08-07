from flask import Blueprint

bp = Blueprint('hello', __name__)

@bp.route("/")
def hello_world():
    return "<p>Hello, World</p>"

@bp.route("/hello")
def hello_world2():
    return "<p>Hello, World2</p>"