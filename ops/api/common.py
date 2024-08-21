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
    edit = data.get("edit")
    req_format = data.get("format")
    if not constants.is_support_format(req_format):
        return make_response("Unsupported content format", 400)
    format, current, c_yml = config_handler.parse_content(
        data.get("content"), format=req_format
    )
    if format == constants.YAML:
        # patch
        suc, msg = config_handler.yaml_patch_content(edit, current)
        if suc is False:
            return make_response(msg, 400)
        return {
            "format": format,
            "content": data.get("content"),
            "next_content": config_handler.yaml_to_string(current, c_yml),
        }
    elif format == constants.PROPERTIES:
        # patch
        suc, msg = config_handler.properties_patch_content(edit, current)
        if suc is False:
            return make_response(msg, 400)
        return {
            "format": format,
            "content": data.get("content"),
            "next_content": config_handler.properties_to_string(current),
        }
    else:
        return make_response("Unsupported content format", 400)


@bp.route("/common/v1/delete_content", methods=["POST"])
def delete_content():
    schema = EditContentSchema()
    data = None
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(err.messages), 400
    edit = data.get("edit")
    req_format = data.get("format")
    if not constants.is_support_format(req_format):
        return make_response("Unsupported content format", 400)
    format, current, c_yml = config_handler.parse_content(
        data.get("content"), format=req_format
    )

    if format == constants.YAML:
        # patch
        suc, msg = config_handler.yaml_delete_content(edit, current)
        if suc is False:
            return make_response(msg, 400)
        return {
            "format": format,
            "content": data.get("content"),
            "next_content": config_handler.yaml_to_string(current, c_yml),
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
        return make_response("Unsupported content format", 400)
