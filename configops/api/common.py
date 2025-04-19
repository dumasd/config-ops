from flask import Blueprint, request
import logging
from marshmallow import Schema, fields, EXCLUDE
from configops.utils import config_handler
from jinja2 import Template
import os

bp = Blueprint("common", __name__, url_prefix=os.getenv("FLASK_APPLICATION_ROOT", "/"))

logger = logging.getLogger(__name__)


class EditContentSchema(Schema):
    content = fields.Str(required=True)
    edit = fields.Str(required=True)
    format = fields.Str(required=True)


class ReplaceJinjaTemplateSchema(Schema):
    templateFile = fields.Str(required=True)
    outputFile = fields.Str(required=True)
    vars = fields.Dict()

    class Meta:
        unknown = EXCLUDE


@bp.route("/common/v1/patch_content", methods=["POST"])
def patch_content():
    data = EditContentSchema().load(request.get_json())
    return config_handler.patch_by_str(
        data.get("content"), data.get("edit"), data.get("format")
    )


@bp.route("/common/v1/delete_content", methods=["POST"])
def delete_content():
    data = EditContentSchema().load(request.get_json())
    return config_handler.delete_by_str(
        data.get("content"), data.get("edit"), data.get("format")
    )


@bp.route("/common/v1/sql_check", methods=["POST"])
def check_sql():
    """
    检查SQL合法性
    """
    logger.log("SQL检查")


@bp.route("/common/v1/replace_jinja_template", methods=["POST"])
def replace_jinja_template():
    data = ReplaceJinjaTemplateSchema().load(request.get_json())
    template_file = data.get("templateFile")
    output_file = data.get("outputFile")
    variables = data.get("vars")

    with open(template_file, "r", encoding="utf-8") as file:
        template = Template(file.read())

    renderStr = template.render(variables)

    with open(output_file, "w", encoding="utf-8") as file:
        file.write(renderStr)
    return "OK"
