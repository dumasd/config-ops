import logging, os
from flask import Blueprint, make_response, request, current_app
from configops.utils import config_validator
from marshmallow import Schema, fields, EXCLUDE
from configops.utils import nacos_client
from configops.utils.exception import ConfigOpsException, ChangeLogException
from configops.changelog.nacos_change import NacosChangeLog
from configops.config import get_nacos_cfg

bp = Blueprint("nacos", __name__, url_prefix=os.getenv("FLASK_APPLICATION_ROOT", "/"))

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
    allowedDataIds = fields.List(fields.Str(), required=False)

    class Meta:
        unknown = EXCLUDE


class ApplyChangeSetSchema(Schema):
    nacosId = fields.Str(required=True)
    changeSetId = fields.Str(required=False)
    changeSetIds = fields.List(fields.Str(), required=True)
    changes = fields.List(fields.Nested(NacosConfigSchema), required=True)

    class Meta:
        unknown = EXCLUDE


@bp.route("/nacos/v1/get_change_set", methods=["POST"])
def get_change_set():
    data = GetChangeSetSchema().load(request.get_json())
    nacos_id = data["nacosId"]
    nacosCfg = get_nacos_cfg(nacos_id)
    if nacosCfg is None:
        return make_response(f"Nacos ID not found in config file: {nacos_id}", 404)

    client = nacos_client.ConfigOpsNacosClient(
        server_addresses=nacosCfg.get("url"),
        username=nacosCfg.get("username"),
        password=nacosCfg.get("password"),
    )
    count = data.get("count", 0)
    contexts = data.get("contexts")
    variables = data.get("vars", {})
    changelog_file = data.get("changeLogFile")
    allowed_data_ids = data.get("allowedDataIds")

    try:
        nacosChangeLog = NacosChangeLog(changelog_file=changelog_file, app=current_app)
        result = nacosChangeLog.fetch_multi(
            client=client,
            nacos_id=nacos_id,
            count=count,
            contexts=contexts,
            vars=variables,
            allowed_data_ids=allowed_data_ids,
        )
        keys = ["ids", "changes"]
        return dict(zip(keys, result))
    except ChangeLogException as err:
        logger.error("Nacos changelog invalid.", exc_info=True)
        return make_response(f"Nacos changelog invalid. {str(err)}", 400)
    except KeyError as err:
        logger.error("Vars missing key", exc_info=True)
        return make_response(f"Vars missing key: {str(err)}", 400)


@bp.route("/nacos/v1/apply_change_set", methods=["POST"])
def apply_change_set():
    data = ApplyChangeSetSchema().load(request.get_json())
    nacos_id = data.get("nacosId")
    change_set_ids = data.get("changeSetIds")
    changes = data.get("changes")

    nacosCfg = get_nacos_cfg(nacos_id)
    if nacosCfg == None:
        return make_response(f"Nacos ID not found in config file: {nacos_id}", 404)
    client = nacos_client.ConfigOpsNacosClient(
        server_addresses=nacosCfg.get("url"),
        username=nacosCfg.get("username"),
        password=nacosCfg.get("password"),
    )

    def push_changes():
        for change in changes:
            namespace = change.get("namespace")
            group = change.get("group")
            data_id = change.get("dataId")
            content = change.get("content")
            _format = change.get("format")
            if content is None or len(content.strip()) == 0:
                raise ConfigOpsException(
                    f"Push content is empty. namespace:{namespace}, group:{group}, data_id:{data_id}"
                )
            validation_bool, validation_msg = config_validator.validate_content(
                content, _format
            )
            if not validation_bool:
                raise ConfigOpsException(
                    f"Push content format invalid. namespace:{namespace}, group:{group}, data_id:{data_id}, format:{_format}. {validation_msg}"
                )

        for change in changes:
            namespace = change.get("namespace")
            group = change.get("group")
            data_id = change.get("dataId")
            content = change.get("content")
            _format = change.get("format")
            client.namespace = namespace
            res = client.publish_config_post(
                data_id=data_id, group=group, content=content, config_type=_format
            )
            if not res:
                raise ConfigOpsException(
                    f"Push config fail. namespace:{namespace}, group:{group}, data_id:{data_id}"
                )

    try:
        NacosChangeLog.apply_changes(change_set_ids, nacos_id, push_changes)
    except Exception as ex:
        logger.error(f"Apply config error. {ex}", stack_info=True)
        return make_response(f"Apply config error:{str(ex)}", 500)
    return "OK"
