from flask import Blueprint, jsonify, make_response, request, current_app
import logging, jsonschema
from configops.utils import constants, config_handler, config_validator
from marshmallow import Schema, fields, ValidationError, EXCLUDE
from configops.utils import nacos_client
from configops.utils.exception import ConfigOpsException, ChangeLogException
from configops.changelog.nacos_change import NacosChangeLog, apply_changes
from configops.config import get_nacos_cfg

bp = Blueprint("nacos", __name__)

logger = logging.getLogger(__name__)


class GetConfigsSchema(Schema):
    nacosId = fields.Str(required=True)
    namespaces = fields.List(fields.Str, required=True)

    class Meta:
        unknown = EXCLUDE


class ModifyPreviewSchema(Schema):
    nacosId = fields.Str(required=True)
    namespace = fields.Str(required=True)
    group = fields.Str(required=True)
    dataId = fields.Str(required=True)
    patchContent = fields.Str(required=False)
    fullContent = fields.Str(required=False)

    class Meta:
        unknown = EXCLUDE


class NacosConfigSchema(Schema):
    id = fields.Str(required=False)
    namespace = fields.Str(required=True)
    group = fields.Str(required=True)
    dataId = fields.Str(required=True)
    content = fields.Str(required=True)
    format = fields.Str(required=True)
    deleteContent = fields.Str(required=False)
    nextContent = fields.Str(required=False)
    patchContent = fields.Str(required=False)

    class Meta:
        unknown = EXCLUDE


class ModifyConfirmSchema(Schema):
    nacosId = fields.Str(required=True)
    namespace = fields.Str(required=True)
    group = fields.Str(required=True)
    dataId = fields.Str(required=True)
    content = fields.Str(required=True)
    format = fields.Str(required=True)

    class Meta:
        unknown = EXCLUDE


class GetChangeSetSchema(Schema):
    nacosId = fields.Str(required=True)
    changeLogFile = fields.Str(required=True)
    count = fields.Int(required=False)
    contexts = fields.Str(required=False)
    vars = fields.Dict()

    class Meta:
        unknown = EXCLUDE


class ApplyChangeSetSchema(Schema):
    nacosId = fields.Str(required=True)
    changeSetId = fields.Str(required=False)
    changeSetIds = fields.List(fields.Str(), required=True)
    changes = fields.List(fields.Nested(NacosConfigSchema), required=True)

    class Meta:
        unknown = EXCLUDE


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
    nacos_id = data.get("nacosId")
    namespace = data.get("namespace")
    group = data.get("group")
    data_id = data.get("dataId")
    nacosConfig = get_nacos_cfg(nacos_id)
    if nacosConfig == None:
        return make_response("Nacos instance not found", 404)

    client = nacos_client.ConfigOpsNacosClient(
        server_addresses=nacosConfig.get("url"),
        username=nacosConfig.get("username"),
        password=nacosConfig.get("password"),
        namespace=namespace,
    )
    client.get_config_detail()
    configs = client.get_configs(no_snapshot=True, group=group)
    pageItems = configs.get("pageItems")

    for item in pageItems:
        if item.get("dataId") == data_id:
            item["format"] = item["type"]
            item["namespace"] = item["tenant"]
            return item
    # 配置不存在，当成新配置处理
    return {
        "id": "",
        "content": "",
        "tenant": namespace,
        "group": group,
        "dataId": data_id,
        "type": "",
        "format": "",
    }


@bp.route("/nacos/v1/namespaces", methods=["GET"])
def get_namespace_list():
    """
    获取namespace_list列表
    """
    nacos_id = request.args.get("nacosId")
    nacosConfig = get_nacos_cfg(nacos_id)
    if nacosConfig == None:
        return make_response("Nacos instance not found", 404)
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
    nacos_id = data.get("nacosId")
    namespaces = data.get("namespaces")
    nacosCfg = get_nacos_cfg(nacos_id)
    if nacosCfg == None:
        return make_response("Nacos config not found", 404)
    client = nacos_client.ConfigOpsNacosClient(
        server_addresses=nacosCfg.get("url"),
        username=nacosCfg.get("username"),
        password=nacosCfg.get("password"),
    )
    result = []
    for namespace in namespaces:
        client.namespace = namespace
        configs = client.get_configs(no_snapshot=True, page_size=9000)
        result.extend(configs.get("pageItems"))
    for item in result:
        item["format"] = item["type"]
        item["namespace"] = item["tenant"]

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

    nacos_id = data.get("nacosId")
    nacosCfg = get_nacos_cfg(nacos_id)
    if nacosCfg == None:
        return "Nacos instance not found", 404

    namespace_id = data.get("namespace_id")
    group = data.get("group")
    data_id = data.get("dataId")
    patch_content = data.get("patchContent")
    full_content = data.get("fullContent")

    # 1. 从nacos捞当前配置
    client = nacos_client.ConfigOpsNacosClient(
        server_addresses=nacosCfg.get("url"),
        username=nacosCfg.get("username"),
        password=nacosCfg.get("password"),
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
            "nextContent": config_handler.yaml_to_string(current, c_yml),
            "nacosUrl": nacosCfg.get("url"),
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
            "nextContent": config_handler.properties_to_string(current),
            "nacosUrl": nacosCfg.get("url"),
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

    nacos_id = data.get("nacosId")
    namespace = data.get("namespace")
    group = data.get("group")
    data_id = data.get("dataId")
    content = data.get("content")
    format = data.get("format")

    # 格式校验
    validation_bool, validation_msg = config_validator.validate_content(content, format)
    if not validation_bool:
        return make_response(validation_msg, 400)

    if content is None or len(content.strip()) == 0:
        return make_response("Content is blank", 400)

    nacosCfg = get_nacos_cfg(nacos_id)
    if nacosCfg == None:
        return make_response("Nacos instance not found", 400)

    client = nacos_client.ConfigOpsNacosClient(
        server_addresses=nacosCfg.get("url"),
        username=nacosCfg.get("username"),
        password=nacosCfg.get("password"),
        namespace=namespace,
    )

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


@bp.route("/nacos/v1/get_change_set", methods=["POST"])
def get_change_set():
    schema = GetChangeSetSchema()
    data = None
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(err.messages), 400

    nacos_id = data["nacosId"]

    nacosCfg = get_nacos_cfg(nacos_id)
    if nacosCfg is None:
        return make_response("Nacos instance not found", 404)

    client = nacos_client.ConfigOpsNacosClient(
        server_addresses=nacosCfg.get("url"),
        username=nacosCfg.get("username"),
        password=nacosCfg.get("password"),
    )
    count = data.get("count", 0)
    contexts = data.get("contexts")
    vars = data.get("vars", {})
    changelogFile = data.get("changeLogFile")

    try:
        nacosChangeLog = NacosChangeLog(changelogFile=changelogFile)
        result = nacosChangeLog.fetch_multi(client, nacos_id, count, contexts, vars)
        keys = ["ids", "changes"]
        return dict(zip(keys, result))
    except ChangeLogException as err:
        logger.error("Nacos changelog invalid.", exc_info=True)
        return make_response(f"Nacos changelog invalid. {err}", 400)
    except KeyError as err:
        logger.error("Vars missing key", exc_info=True)
        return make_response(f"Vars missing key: {err}", 400)


@bp.route("/nacos/v1/apply_change_set", methods=["POST"])
def apply_change_set():
    schema = ApplyChangeSetSchema()
    data = None
    try:
        data = schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(err.messages), 400
    nacos_id = data.get("nacosId")
    change_set_ids = data.get("changeSetIds")
    changes = data.get("changes")

    nacosCfg = get_nacos_cfg(nacos_id)
    if nacosCfg == None:
        return make_response("Nacos instance not found", 404)
    client = nacos_client.ConfigOpsNacosClient(
        server_addresses=nacosCfg.get("url"),
        username=nacosCfg.get("username"),
        password=nacosCfg.get("password"),
    )

    def push_changes():
        pass
        for change in changes:
            namespace = change.get("namespace")
            group = change.get("group")
            data_id = change.get("dataId")
            content = change.get("content")
            format = change.get("format")
            if content is None or len(content.strip()) == 0:
                raise ConfigOpsException(
                    f"Push content is empty. namespace:{namespace}, group:{group}, data_id:{data_id}"
                )
            validation_bool, validation_msg = config_validator.validate_content(
                content, format
            )
            if not validation_bool:
                raise ConfigOpsException(
                    f"Push content format invalid. namespace:{namespace}, group:{group}, data_id:{data_id}, format:{format}. {validation_msg}"
                )

        for change in changes:
            namespace = change.get("namespace")
            group = change.get("group")
            data_id = change.get("dataId")
            content = change.get("content")
            format = change.get("format")
            client.namespace = namespace
            res = client.publish_config_post(
                data_id=data_id, group=group, content=content, config_type=format
            )
            if not res:
                raise ConfigOpsException(
                    f"Push config fail. namespace:{namespace}, group:{group}, data_id:{data_id}"
                )

    try:
        apply_changes(change_set_ids, nacos_id, push_changes)
    except Exception as ex:
        logger.error(f"Apply config error. {ex}")
        return make_response(f"Apply config error:{ex}", 500)
    return "OK"
