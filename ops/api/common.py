from flask import Blueprint, jsonify, make_response, request, current_app
import logging
from marshmallow import Schema, fields, ValidationError
from ops.utils import config_handler, constants

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

    needPatch = True
    if len(content.strip()) == 0:
        needPatch = False
        # 内容为空
        format, current, yml = config_handler.parse_content(edit, format=type)
    else:
        format, current, yml = config_handler.parse_content(content, format=type)

    format, current, yml = config_handler.parse_content(
        data.get("content"), format=type
    )

    if needPatch:
        if format == constants.YAML:
            suc, msg = config_handler.yaml_patch_content(edit, current)
            if suc is False:
                return make_response(msg, 400)
            return {
                "format": format,
                "content": data.get("content"),
                "next_content": config_handler.yaml_to_string(current, yml),
            }
        elif format == constants.PROPERTIES:
            suc, msg = config_handler.properties_patch_content(edit, current)
            if suc is False:
                return make_response(msg, 400)
            return {
                "format": format,
                "content": data.get("content"),
                "next_content": config_handler.properties_to_string(current),
            }
        else:
            return make_response("Unsupported patch format", 400)
    else:
        if format == constants.UNKNOWN:
            format = constants.TEXT
        return {"format": format, "content": content, "next_content": edit}


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

    if len(content.strip()) == 0:
        return {"format": type, "content": "", "next_content": ""}

    format, current, yml = config_handler.parse_content(
        data.get("content"), format=type
    )

    if format == constants.YAML:
        # patch
        suc, msg = config_handler.yaml_delete_content(edit, current)
        if suc is False:
            return make_response(msg, 400)
        return {
            "format": format,
            "content": data.get("content"),
            "next_content": config_handler.yaml_to_string(current, yml),
        }
    elif format == constants.PROPERTIES:
        # patch
        suc, msg = config_handler.properties_delete_content(edit, current)
        if suc is False:
            return make_response(msg, 400)
        return {
            "format": format,
            "content": data.get("content"),
            "next_content": config_handler.properties_to_string(current),
        }
    else:
        return make_response("Unsupported delete format", 400)


@bp.route("/common/v1/sql_check", methods=["POST"])
def check_sql():
    """
    检查SQL合法性
    """
    logger.log("SQL检查")
