from flask import Blueprint, jsonify, make_response, request, current_app
import logging
from marshmallow import Schema, fields, ValidationError
from configops.utils import config_handler, constants

bp = Blueprint("common", __name__)

logger = logging.getLogger(__name__)


class EditContentSchema(Schema):
    content = fields.Str(required=True)
    edit = fields.Str(required=True)
    format = fields.Str(required=True)


@bp.route("/common/v1/patch_content", methods=["POST"])
def patch_content():
    schema = EditContentSchema()
    data = None
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(err.messages), 400
    content = data.get("content")
    edit = data.get("edit")
    type = data.get("format")
    return config_handler.patch_by_str(content, edit, type)


@bp.route("/common/v1/delete_content", methods=["POST"])
def delete_content():
    schema = EditContentSchema()
    data = None
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(err.messages), 400
    content = data.get("content")
    edit = data.get("edit")
    type = data.get("format")

    return config_handler.delete_by_str(content, edit, type)


@bp.route("/common/v1/sql_check", methods=["POST"])
def check_sql():
    """
    检查SQL合法性
    """
    logger.log("SQL检查")
