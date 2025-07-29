import logging, os, string
from configops.changelog import changelog_utils
from configops.utils import config_handler, config_validator
from configops.utils.constants import ChangelogExeType, SystemType, extract_version
from configops.utils.exception import ChangeLogException, ConfigOpsException
from configops.config import get_config
from ruamel import yaml as ryaml
from jsonschema import Draft7Validator, ValidationError
from configops.utils.nacos_client import ConfigOpsNacosClient
from configops.database.db import db, ConfigOpsChangeLog, ConfigOpsChangeLogChanges


logger = logging.getLogger(__name__)

schema = {
    "type": "object",
    "properties": {
        "nacosChangeLog": {
            "type": ["array", "null"],
            "items": [
                {
                    "type": "object",
                    "properties": {
                        "changeSet": {
                            "type": "object",
                            "description": "The change set",
                            "properties": {
                                "id": {
                                    "type": ["string", "number"],
                                    "description": "The change set id",
                                },
                                "author": {
                                    "type": "string",
                                    "description": "The change set author",
                                },
                                "comment": {
                                    "type": "string",
                                    "description": "The change set comment",
                                },
                                "ignore": {
                                    "type": "boolean",
                                    "default": "false",
                                    "description": "The change set is ignored",
                                },
                                "context": {
                                    "type": "string",
                                    "description": "The change set context. Multiple are separated by commas",
                                },
                                "runOnChange": {
                                    "type": "boolean",
                                    "default": "false",
                                    "description": "Re-run when the change set changed.",
                                },
                                "changes": {
                                    "type": "array",
                                    "items": [
                                        {
                                            "type": "object",
                                            "properties": {
                                                "namespace": {"type": "string"},
                                                "group": {"type": "string"},
                                                "dataId": {"type": "string"},
                                                "delete": {
                                                    "type": "boolean",
                                                    "default": "false",
                                                    "description": "Whether to delete the configuration",
                                                },
                                                "format": {
                                                    "type": "string",
                                                    "pattern": "^(yaml|properties|json|text)$",
                                                },
                                                "patchContent": {"type": "string"},
                                                "deleteContent": {"type": "string"},
                                            },
                                            "required": [
                                                "namespace",
                                                "group",
                                                "dataId",
                                            ],
                                        }
                                    ],
                                },
                            },
                            "required": ["changes"],
                        }
                    },
                },
                {
                    "type": "object",
                    "properties": {
                        "include": {
                            "type": "object",
                            "properties": {
                                "file": {"type": "string"},
                                "ignore": {"type": "boolean", "default": "false"},
                            },
                        },
                    },
                },
            ],
        },
    },
    "required": ["nacosChangeLog"],
}


class NacosChangeLog:
    def __init__(self, changelog_file=None, app=None):
        self.changelog_file = changelog_file
        self.app = app
        self.__init_change_log__()

    def __init_change_log__(self):
        change_set_dict = {}
        change_set_list = []

        if os.path.isfile(self.changelog_file):
            changelog_data = None
            with open(self.changelog_file, "r", encoding="utf-8") as file:
                try:
                    yaml = ryaml.YAML()
                    yaml.preserve_quotes = True
                    changelog_data = yaml.load(file)
                    validator = Draft7Validator(schema)
                    validator.validate(changelog_data)
                except ValidationError as e:
                    raise ChangeLogException(
                        f"Nacos changelog validation error: {self.changelog_file} \n{e}"
                    )

            base_dir = os.path.dirname(self.changelog_file)
            changelog_file_name = os.path.basename(self.changelog_file)
            changelog_file_id = os.path.splitext(changelog_file_name)[0]
            items = changelog_data.get("nacosChangeLog", None)

            if items:
                include_files = []
                for item in items:
                    change_set_obj = item.get("changeSet")
                    include_obj = item.get("include")
                    if change_set_obj:
                        change_set_id = str(change_set_obj.get("id", changelog_file_id))
                        change_set_obj["id"] = change_set_id
                        ignore = change_set_obj.get("ignore", False)
                        change_set_obj["ignore"] = ignore
                        if change_set_dict.get(change_set_id) is not None:
                            raise ChangeLogException(
                                f"Repeat change set id {change_set_id}"
                            )

                        change_set_obj["filename"] = changelog_file_name
                        change_set_dict[change_set_id] = change_set_obj
                        changes = change_set_obj["changes"]

                        changeSetChangeDict = {}
                        for change in changes:
                            namespace = change.get("namespace", "")
                            group = change["group"]
                            dataId = change["dataId"]

                            _format = change.get("format")
                            delete = change.get("delete", False)

                            config_key = f"{namespace}/{group}/{dataId}"

                            if changeSetChangeDict.get(config_key) is not None:
                                raise ChangeLogException(
                                    f"Nacos repeated change. changelogFile: {self.changelog_file}, changeSetId:{change_set_id}, namespace:{namespace}, group:{group}, dataId:{dataId}"
                                )
                            changeSetChangeDict[config_key] = change

                            if delete:
                                continue

                            if not _format:
                                raise ChangeLogException(
                                    f"Nacos change format is required. changelogFile: {self.changelog_file}, changeSetId: {change_set_id}, namespace: {namespace}, group: {group}, dataId: {dataId}"
                                )

                            patch_content = change.get("patchContent", "").strip()
                            delete_content = change.get("deleteContent", "").strip()
                            if len(patch_content) > 0:
                                suc, msg = config_validator.validate_content(
                                    patch_content, _format
                                )
                                if not suc:
                                    raise ChangeLogException(
                                        f"Nacos patchContent Invalid!!! changelogFile: {self.changelog_file}, changeSetId: {change_set_id}, namespace: {namespace}, group: {group}, dataId: {dataId}, format: {_format}. errorMsg: {msg}"
                                    )

                            if len(delete_content) > 0:
                                suc, msg = config_validator.validate_content(
                                    delete_content, _format
                                )
                                if not suc:
                                    raise ChangeLogException(
                                        f"Nacos deleteContent Invalid!!! changelogFile: {self.changelog_file}, changeSetId: {change_set_id}, namespace: {namespace}, group: {group}, dataId: {dataId}, format: {_format}. errorMsg: {msg}"
                                    )

                        if not ignore:
                            change_set_list.append(change_set_obj)

                    elif include_obj:
                        # 引用了其他文件
                        file = include_obj["file"]
                        if file in include_files:
                            raise ChangeLogException(
                                f"Repeat include file!!! changelogFile: {self.changelog_file}, file: {file}"
                            )
                        include_files.append(file)
                        child_nacos_change_log = NacosChangeLog(
                            changelog_file=f"{base_dir}/{file}", app=self.app
                        )
                        for change_set_id in child_nacos_change_log.change_set_dict:
                            if change_set_id in change_set_dict:
                                raise ChangeLogException(
                                    f"Repeat changeSetId: {change_set_id}. Please check your changelog"
                                )
                            else:
                                change_set_dict[change_set_id] = (
                                    child_nacos_change_log.change_set_dict[
                                        change_set_id
                                    ]
                                )
                        change_set_list.extend(child_nacos_change_log.change_set_list)

        elif os.path.isdir(self.changelog_file):
            changelogfiles = []
            for dirpath, dirnames, filenames in os.walk(self.changelog_file):
                for filename in filenames:
                    if filename.endswith((".yaml", ".yml")):
                        changelogfiles.append(os.path.join(dirpath, filename))
            # 根据文件名排序
            sorted_changelogfiles = sorted(changelogfiles, key=extract_version)
            for file in sorted_changelogfiles:
                child_nacos_change_log = NacosChangeLog(
                    changelog_file=file, app=self.app
                )
                for change_set_id in child_nacos_change_log.change_set_dict:
                    if change_set_id in change_set_dict:
                        raise ChangeLogException(
                            f"Repeat change set id: {change_set_id}. Please check your changelog"
                        )
                    else:
                        change_set_dict[change_set_id] = (
                            child_nacos_change_log.change_set_dict[change_set_id]
                        )
                change_set_list.extend(child_nacos_change_log.change_set_list)

        else:
            raise ChangeLogException(
                f"Changelog file or folder does not exists: {self.changelog_file}"
            )

        self.change_set_dict = change_set_dict
        self.change_set_list = change_set_list

    def __check_change_log__(
        self, change_set_obj, nacos_id: str, contexts: str, variables: dict
    ) -> bool:
        change_set_id = str(change_set_obj["id"])
        # 计算checksum
        checksum = changelog_utils.get_change_set_checksum(
            {"changes": change_set_obj["changes"]}
        )
        current_filename = change_set_obj["filename"]
        is_execute = True
        log = (
            db.session.query(ConfigOpsChangeLog)
            .filter_by(
                change_set_id=change_set_id,
                system_id=nacos_id,
                system_type=SystemType.NACOS.value,
            )
            .first()
        )
        if log is not None:
            if (
                log.filename
                and len(log.filename) > 0
                and log.filename != current_filename
            ):
                raise ChangeLogException(
                    f"ChangeSetId is already defined in an earlier changelog. changeSetId:{change_set_id}, Current file:{current_filename}, previous file:{log.filename}"
                )
            if ChangelogExeType.FAILED.matches(
                log.exectype
            ) or ChangelogExeType.INIT.matches(log.exectype):
                log.checksum = checksum
            else:
                runOnChange = change_set_obj.get("runOnChange", False)
                if runOnChange and log.checksum != checksum:
                    log.exectype = ChangelogExeType.INIT.value
                    log.checksum = checksum
                else:
                    is_execute = False
        else:
            log = ConfigOpsChangeLog()
            log.change_set_id = change_set_id
            log.system_type = SystemType.NACOS.value
            log.system_id = nacos_id
            log.exectype = ChangelogExeType.INIT.value
            log.author = change_set_obj.get("author", "")
            log.comment = change_set_obj.get("comment", "")
            log.filename = change_set_obj["filename"]
            log.checksum = checksum
            db.session.add(log)

        _secret = None
        if self.app:
            _secret = get_config(self.app, "config.node.secret")

        if _secret:
            nacos_changes = []
            for change in change_set_obj["changes"]:
                nacos_change = change.copy()
                namespace = string.Template(change["namespace"]).substitute(variables)
                group = string.Template(change["group"]).substitute(variables)
                dataId = string.Template(change["dataId"]).substitute(variables)
                nacos_change["namespace"] = namespace
                nacos_change["group"] = group
                nacos_change["dataId"] = dataId
                nacos_changes.append(nacos_change)
            log_changes = (
                db.session.query(ConfigOpsChangeLogChanges)
                .filter_by(
                    change_set_id=change_set_id,
                    system_id=nacos_id,
                    system_type=SystemType.NACOS.value,
                )
                .first()
            )
            if log_changes is None:
                log_changes = ConfigOpsChangeLogChanges(
                    change_set_id=change_set_id,
                    system_type=SystemType.NACOS.value,
                    system_id=nacos_id,
                    changes=changelog_utils.pack_changes(
                        nacos_changes, _secret
                    ),
                )
                db.session.add(log_changes)
            else:
                log_changes.changes = changelog_utils.pack_changes(
                    nacos_changes, _secret
                )

        return is_execute

    def fetch_multi(
        self,
        client: ConfigOpsNacosClient,
        nacos_id: str,
        count: int = 0,
        contexts: str = None,
        vars: dict = {},
        check_log: bool = True,
        spec_changesets=[],
        allowed_data_ids: list = None,
    ):
        """
        获取多个当前需要执行的changeset
        """
        idx = 0
        remote_configs_cache = {}
        alter_change_configs = {}
        delete_change_configs = {}
        change_set_ids = []
        for change_set_obj in self.change_set_list:
            change_set_id = str(change_set_obj["id"])
            changelog_filename = change_set_obj["filename"]
            # 判断是否在指定的contexts里面
            change_set_ctx = change_set_obj.get("context")
            if not changelog_utils.is_ctx_included(contexts, change_set_ctx):
                continue

            if (
                spec_changesets
                and len(spec_changesets) > 0
                and change_set_id not in spec_changesets
            ):
                continue

            is_execute = True
            # 查询log
            if check_log:
                is_execute = self.__check_change_log__(
                    change_set_obj, nacos_id, contexts, vars
                )

            if is_execute:
                logger.info(f"Found change set log: {change_set_id}")
                change_set_ids.append(change_set_id)
                for change in change_set_obj["changes"]:
                    logger.info(f"current change: {change}")
                    namespace = string.Template(change["namespace"]).substitute(vars)
                    group = string.Template(change["group"]).substitute(vars)
                    dataId = string.Template(change["dataId"]).substitute(vars)
                    delete = change.get("delete", False)
                    _format = change.get("format")

                    if (
                        allowed_data_ids
                        and len(allowed_data_ids) > 0
                        and dataId not in allowed_data_ids
                    ):
                        raise ChangeLogException(
                            f"Config dataId is not allowed. changelogFile:{changelog_filename}, changeSetId:{change_set_id}, namespace/group/dataId:{namespace}/{group}/{dataId}, allowed dataId:{allowed_data_ids}"
                        )
                    nacos_config = change.copy()
                    nacos_config["namespace"] = namespace
                    nacos_config["group"] = group
                    nacos_config["dataId"] = dataId
                    nacos_config["delete"] = delete
                    nacos_config["content"] = ""
                    nacos_config["id"] = ""

                    config_key = f"{namespace}/{group}/{dataId}"

                    if delete:
                        alter_change_configs.pop(config_key, None)
                        delete_change_configs[config_key] = nacos_config
                        continue

                    if not _format:
                        raise ChangeLogException(
                            f"Config format missing. changelogFile:{changelog_filename}, changeSetId:{change_set_id}, namespace/group/dataId:{namespace}/{group}/{dataId}"
                        )

                    delete_change_configs.pop(config_key, None)

                    remote_config, _ = self._get_remote_config(
                        remote_configs_cache, namespace, group, dataId, client
                    )
                    if remote_config:
                        remote_config_format = remote_config["type"]
                        remote_config_content = remote_config["content"]

                        if remote_config_format != _format:
                            raise ChangeLogException(
                                f"Config format not match. changelogFile:{changelog_filename}, changeSetId:{change_set_id}, namespace/group/dataId:{namespace}/{group}/{dataId}, changelogFormat:{_format}, nacosFormat:{remote_config_format}"
                            )

                        if len(remote_config_content.strip()) > 0:
                            suc, msg = config_validator.validate_content(
                                remote_config_content, _format
                            )
                            if not suc:
                                raise ChangeLogException(
                                    f"Current Nacos Config Content Invalid!!! changelogFile:{changelog_filename}, changeSetId:{change_set_id}, namespace/group/dataId:{namespace}/{group}/{dataId}, format: {_format}. errorMsg: {msg}"
                                )

                        nacos_config["content"] = remote_config_content
                        nacos_config["id"] = remote_config["id"]

                    next_content = nacos_config.get("content")
                    previous_config = alter_change_configs.get(config_key)
                    if previous_config:
                        next_content = previous_config["nextContent"]

                    # 直接追加内容，放到 nextContent
                    next_content_res = config_handler.delete_patch_by_str(
                        next_content,
                        _format,
                        nacos_config.get("deleteContent", ""),
                        nacos_config.get("patchContent", ""),
                    )
                    nacos_config["nextContent"] = next_content_res["nextContent"]

                    # 所有patch和delete也聚合在一起
                    if previous_config:
                        delete_content = nacos_config.get("deleteContent", "")
                        patch_content = nacos_config.get("patchContent", "")
                        # Delete and Patch pathContent
                        res = config_handler.delete_patch_by_str(
                            previous_config.get("patchContent", ""),
                            _format,
                            delete_content,
                            patch_content,
                        )
                        nacos_config["patchContent"] = res["nextContent"]

                        # Delete and Patch deleteContent
                        res = config_handler.delete_patch_by_str(
                            previous_config.get("deleteContent", ""),
                            _format,
                            patch_content,
                            delete_content,
                        )
                        nacos_config["deleteContent"] = res["nextContent"]

                    alter_change_configs[config_key] = nacos_config

            idx += 1
            if count > 0 and idx >= count:
                break

        if check_log:
            db.session.commit()
        return (
            change_set_ids,
            list(alter_change_configs.values()),
            list(delete_change_configs.values()),
        )

    def _get_remote_config(
        self,
        remote_configs_cache,
        namespace,
        group,
        dataId,
        client: ConfigOpsNacosClient,
    ):
        namespace_group_key = f"{namespace}/{group}"
        namespace_group_configs = remote_configs_cache.get(namespace_group_key)
        if namespace_group_configs is None:
            client.namespace = namespace
            resp = client.get_configs(no_snapshot=True, group=group)
            namespace_group_configs = resp.get("pageItems")
            remote_configs_cache[namespace_group_key] = namespace_group_configs
        for item in namespace_group_configs:
            if item.get("dataId") == dataId:
                return item, namespace_group_configs
        return None, namespace_group_configs

    @staticmethod
    def apply_changes(
        change_set_ids,
        nacos_id: str,
        client: ConfigOpsNacosClient,
        changes: list,
        delete_changes: list,
    ):
        logs = (
            db.session.query(ConfigOpsChangeLog)
            .filter(
                ConfigOpsChangeLog.change_set_id.in_(change_set_ids),
                ConfigOpsChangeLog.system_id == nacos_id,
                ConfigOpsChangeLog.system_type == SystemType.NACOS.value,
            )
            .all()
        )

        if logs is None or len(logs) == 0:
            raise ChangeLogException(
                f"Change log not found. change_set_ids:{change_set_ids}"
            )

        try:
            NacosChangeLog.push_remote(client, changes, delete_changes)
            for log in logs:
                log.exectype = ChangelogExeType.EXECUTED.value
        except Exception as e:
            for log in logs:
                log.exectype = ChangelogExeType.FAILED.value
            raise e
        finally:
            db.session.commit()

    @staticmethod
    def push_remote(client: ConfigOpsNacosClient, changes: list, delete_changes: list):
        if delete_changes and len(delete_changes) > 0:
            for change in delete_changes:
                namespace = change.get("namespace")
                group = change.get("group")
                data_id = change.get("dataId")
                client.namespace = namespace
                res = client.remove_config(data_id=data_id, group=group)
                if not res:
                    raise ConfigOpsException(
                        f"Delete config fail. namespace:{namespace}, group:{group}, data_id:{data_id}"
                    )

        if changes and len(changes) > 0:
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
