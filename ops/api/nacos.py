from flask import Blueprint, jsonify, make_response, request, current_app
import nacos
import logging
from ops.utils import config_handler, constants
from marshmallow import Schema, fields, ValidationError
from ops.utils import nacos_client

bp = Blueprint("nacos", __name__)

logger = logging.getLogger(__name__)


class GetConfigsSchema(Schema):
    nacos_id = fields.Str(required=True)
    namespaces = fields.List(fields.Str, required=True)


class GetConfigSchema(Schema):
    nacos_id = fields.Str(required=True)
    namespace_id = fields.Str(required=False)  # 不传就为public空间
    group = fields.Str(required=True)
    data_id = fields.Str(required=True)


class ModifyPreviewSchema(Schema):
    nacos_id = fields.Str(required=True)
    namespace_id = fields.Str(required=True)  # 不传就为public空间
    group = fields.Str(required=True)
    data_id = fields.Str(required=True)
    patch_content = fields.Str(required=False)
    full_content = fields.Str(required=False)


class ModifyConfirmSchema(Schema):
    nacos_id = fields.Str(required=True)
    namespace_id = fields.Str(required=True)  # 不传就为public空间
    group = fields.Str(required=True)
    data_id = fields.Str(required=True)
    content = fields.Str(required=True)
    format = fields.Str(required=True)


def get_nacos_config(nacos_id):
    nacosConfigs = current_app.config["nacos"]
    nacosConfig = nacosConfigs[nacos_id]
    return nacosConfig


@bp.route("/nacos/v1/list", methods=["GET"])
def get_nacos_list():
    """获取Nacos服务列表"""
    configs = current_app.config["nacos"]
    list = []
    for k in configs:
        nc = configs[k]
        list.append({"nacos_id": k, "url": nc["url"]})
    return list


@bp.route("/nacos/v1/config", methods=["GET"])
def get_config():
    """获取指定配置"""
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
    format, current, c_yml = config_handler.parse_content(current_content)

    if format == constants.UNKNOWN:
        return "Unsupport format", 404
    return {"format": format, "content": current_content or ""}


@bp.route("/nacos/v1/namespaces", methods=["GET"])
def get_namespace_list():
    """
    获取namespace_list列表
    """
    nacos_id = request.args.get("nacos_id")
    nacosConfig = get_nacos_config(nacos_id)
    if nacosConfig == None:
        return make_response("Nacos config not found", 404)
    client = nacos_client.ConfigOpsNacosClient(
        server_addresses=nacosConfig.get("url"),
        username=nacosConfig.get("username"),
        password=nacosConfig.get("password"),
    )
    resp = client.list_namespace()
    if resp.get("code") != 200:
        return resp.get("message"), 500
    return resp.get("data")


@bp.route("/nacos/v1/configs", methods=["POST"])
def get_configs():
    schema = GetConfigsSchema()
    data = None
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(err.messages), 400
    nacos_id = data.get("nacos_id")
    namespaces = data.get("namespaces")
    nacosConfig = get_nacos_config(nacos_id)
    if nacosConfig == None:
        return make_response("Nacos config not found", 404)
    client = nacos_client.ConfigOpsNacosClient(
        server_addresses=nacosConfig.get("url"),
        username=nacosConfig.get("username"),
        password=nacosConfig.get("password"),
    )
    result = []
    for namespace in namespaces:
        client.namespace = namespace
        configs = client.get_configs(no_snapshot=True, page_size=9000)
        result.extend(configs.get("pageItems"))
    return result


@bp.route("/nacos/v1/config/modify", methods=["POST"])
def modify_preview():
    """
    修改预览
    """
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
        format, current, c_yml = config_handler.parse_content(current_content)
    elif full_content is not None and len(full_content.strip()) > 0:
        format, current, c_yml = config_handler.parse_content(full_content)
        # patch
        need_cpx = False
    else:
        return make_response("Remote config and full content all blank", 400)

    if format == constants.YAML:
        # cpx
        if need_cpx:
            suc, msg = config_handler.yaml_cpx_content(full_content, current)
            if suc is False:
                return make_response(msg, 400)
        # patch
        suc, msg = config_handler.yaml_patch_content(patch_content, current)
        if suc is False:
            return make_response(msg, 400)
        return {
            "format": format,
            "content": current_content or "",
            "next_content": config_handler.yaml_to_string(current, c_yml),
            "nacos_url": nacosConfig.get("url"),
        }
    elif format == constants.PROPERTIES:
        config_handler.properties_cpx_content(full_content, current)
        # cpx
        if need_cpx:
            suc, msg = config_handler.properties_cpx_content(full_content, current)
            if suc is False:
                return make_response(msg, 400)
        # patch
        suc, msg = config_handler.properties_patch_content(patch_content, current)
        if suc is False:
            return make_response(msg, 400)
        return {
            "format": format,
            "content": current_content or "",
            "next_content": config_handler.properties_to_string(current),
            "nacos_url": nacosConfig.get("url"),
        }
    else:
        return make_response("Unsupported content format", 400)


@bp.route("/nacos/v1/config/modify", methods=["PUT"])
def modify_confirm():
    """修改配置"""
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
    format = data.get("format")

    if content is None or len(content.strip()) == 0:
        return make_response("Content is blank", 400)

    nacosConfig = get_nacos_config(nacos_id)
    if nacosConfig == None:
        return make_response("Nacos config not found", 400)
    client = nacos_client.ConfigOpsNacosClient(
        server_addresses=nacosConfig.get("url"),
        username=nacosConfig.get("username"),
        password=nacosConfig.get("password"),
        namespace=namespace_id,
    )

    # current_format, format = None, None

    # current_content = client.get_config(data_id=data_id, group=group, no_snapshot=True)
    # if current_content is not None and len(current_content.strip()) > 0:
    #     current_format, _, _ = config_handler.parse_content(current_content)

    # format, _, _ = config_handler.parse_content(content)

    # if current_format is not None and current_format != format:
    #     make_response(
    #         f"Current content format [{current_format}] not match new content format [{format}]",
    #         400,
    #     )

    # if not constants.is_support_format(format):
    #     return make_response("Unsupported format", 400)

    try:
        res = client.publish_config_post(
            data_id=data_id, group=group, content=content, config_type=format
        )
        if not res:
            return make_response("Publish config unsuccess from nacos", 500)
    except Exception as ex:
        logger.error(f"Publish config error. {ex}")
        return make_response(f"Publish config excaption:{ex}", 500)

    return "OK"
