from flask import Blueprint, jsonify, make_response, request, current_app
import nacos
import logging
from ops.utils import parser, constants
from marshmallow import Schema, fields, ValidationError

bp = Blueprint("nacos", __name__)

logger = logging.getLogger(__name__)


class GetConfigSchema(Schema):
    nacos_id = fields.Str(required=True)
    namespace_id = fields.Str(required=False)  # 不传就为public空间
    group = fields.Str(required=True)
    data_id = fields.Str(required=True)


class ModifyPreviewSchema(Schema):
    nacos_id = fields.Str(required=True)
    namespace_id = fields.Str(required=False)  # 不传就为public空间
    group = fields.Str(required=True)
    data_id = fields.Str(required=True)
    patch_content = fields.Str(required=False)
    full_content = fields.Str(required=False)


class ModifyConfirmSchema(Schema):
    nacos_id = fields.Str(required=True)
    namespace_id = fields.Str(required=False)  # 不传就为public空间
    group = fields.Str(required=True)
    data_id = fields.Str(required=True)
    content = fields.Str(required=True)


def get_nacos_config(nacos_id):
    nacosConfigs = current_app.config["nacos"]
    nacosConfig = nacosConfigs[nacos_id]
    return nacosConfig


""" 获取Nacos服务列表 """


@bp.route("/nacos/v1/list", methods=["GET"])
def get_nacos_list():
    configs = current_app.config["nacos"]
    list = []
    for k in configs:
        nc = configs[k]
        list.append({"nacos_id": k, "url": nc["url"]})
    return list


""" 获取指定配置 """


@bp.route("/nacos/v1/config", methods=["GET"])
def get_config():
    schema = ModifyPreviewSchema()
    data = None
    try:
        data = schema.load(request.args)
    except ValidationError as err:
        return jsonify(err.messages), 400
    nacos_id = data.get("nacos_id")
    namespace_id = data.get("namespace_id")
    group = data.get("group")
    data_id = data.get("data_id")
    nacosConfig = get_nacos_config(nacos_id)
    if nacosConfig == None:
        return make_response("Nacos config not found", 404)
    client = nacos.NacosClient(
        server_addresses=nacosConfig.get("url"),
        username=nacosConfig.get("username"),
        password=nacosConfig.get("password"),
        namespace=namespace_id,
    )
    current_content = client.get_config(data_id=data_id, group=group, no_snapshot=True)
    format, current, c_yml = parser.parse_content(current_content)

    if format == constants.UNKNOWN:
        return "Unsupport format", 404
    return {"format": format, "content": current_content or ""}


""" 修改预览 """


@bp.route("/nacos/v1/config/modify", methods=["POST"])
def modify_preview():
    schema = ModifyPreviewSchema()
    data = None
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(err.messages), 400

    nacos_id = data.get("nacos_id")
    nacosConfig = get_nacos_config(nacos_id)
    if nacosConfig == None:
        return "Nacos config not found", 404

    namespace_id = data.get("namespace_id")
    group = data.get("group")
    data_id = data.get("data_id")
    patch_content = data.get("patch_content")
    full_content = data.get("full_content")

    print(data, nacosConfig)

    # 1. 从nacos捞当前配置
    client = nacos.NacosClient(
        server_addresses=nacosConfig.get("url"),
        username=nacosConfig.get("username"),
        password=nacosConfig.get("password"),
        namespace=namespace_id,
    )
    current_content = client.get_config(data_id=data_id, group=group, no_snapshot=True)

    format, current, c_yml = None, None, None
    need_cpx = True
    if current_content is not None and len(current_content.strip()) > 0:
        # 空内容，以full格式为准
        format, current, c_yml = parser.parse_content(current_content)
    elif full_content is not None and len(full_content.strip()) > 0:
        format, current, c_yml = parser.parse_content(full_content)
        # patch
        need_cpx = False
    else:
        return make_response("Remote config and full content all blank", 400)

    if format == constants.YAML:
        # cpx
        if need_cpx:
            suc, msg = parser.yaml_cpx_content(full_content, current)
            if suc is False:
                return make_response(msg, 400)
        # patch
        suc, msg = parser.yaml_patch_content(patch_content, current)
        if suc is False:
            return make_response(msg, 400)
        return {
            "format": format,
            "content": current_content or "",
            "next_content": parser.yaml_to_string(current, c_yml),
            "nacos_url": nacosConfig.get("url"),
        }
    elif format == constants.PROPERTIES:
        parser.properties_cpx_content(full_content, current)
        # cpx
        if need_cpx:
            suc, msg = parser.properties_cpx_content(full_content, current)
            if suc is False:
                return make_response(msg, 400)
        # patch
        suc, msg = parser.properties_patch_content(patch_content, current)
        if suc is False:
            return make_response(msg, 400)
        return {
            "format": format,
            "content": current_content or "",
            "next_content": parser.properties_to_string(current),
            "nacos_url": nacosConfig.get("url"),
        }
    else:
        return make_response("Unsupported content format", 400)


""" 修改配置 """


@bp.route("/nacos/v1/config/modify", methods=["PUT"])
def modify_confirm():
    schema = ModifyConfirmSchema()
    data = None
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(err.messages), 400

    nacos_id = data.get("nacos_id")
    namespace_id = data.get("namespace_id")
    group = data.get("group")
    data_id = data.get("data_id")
    content = data.get("content")

    if content is None or len(content.strip()) == 0:
        return make_response("Content is blank", 400)

    nacosConfig = get_nacos_config(nacos_id)
    if nacosConfig == None:
        return make_response("Nacos config not found", 400)
    client = nacos.NacosClient(
        server_addresses=nacosConfig.get("url"),
        username=nacosConfig.get("username"),
        password=nacosConfig.get("password"),
        namespace=namespace_id,
    )

    current_format, format = None, None

    current_content = client.get_config(data_id=data_id, group=group, no_snapshot=True)
    if current_content is not None and len(current_content.strip()) > 0:
        current_format, _, _ = parser.parse_content(current_content)

    format, _, _ = parser.parse_content(content)

    if current_format is not None and current_format != format:
        make_response(
            f"Current content format [{current_format}] not match new content format [{format}]",
            400,
        )

    if not constants.is_support_format(format):
        return make_response("Unsupported format", 400)

    try:
        res = client.publish_config(
            data_id=data_id, group=group, content=content, config_type=format
        )
        if not res:
            return make_response("Publish config unsuccess from nacos", 500)
    except Exception as ex:
        return make_response("Publish config excaption", 500)

    return "OK"
