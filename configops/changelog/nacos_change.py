import logging, os, string
from configops.changelog import changelog_utils
from configops.utils import config_handler, config_validator
from configops.utils.constants import ChangelogExeType, SystemType, extract_version
from configops.utils.exception import ChangeLogException
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
                                                "format",
                                            ],
                                        }
                                    ],
                                },
                            },
                            "required": ["id", "changes"],
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
    def __init__(self, changelogFile=None, app=None):
        self.changelogFile = changelogFile
        self.app = app
        self.__init_change_log()

    def __init_change_log(self):
        changeSetDict = {}
        changeSets = []

        if os.path.isfile(self.changelogFile):
            changeLogData = None
            with open(self.changelogFile, "r", encoding="utf-8") as file:
                try:
                    yaml = ryaml.YAML()
                    yaml.preserve_quotes = True
                    changeLogData = yaml.load(file)
                    validator = Draft7Validator(schema)
                    validator.validate(changeLogData)
                except ValidationError as e:
                    raise ChangeLogException(
                        f"Nacos changelog validation error: {self.changelogFile} \n{e}"
                    )

            base_dir = os.path.dirname(self.changelogFile)
            changelog_file_name = os.path.basename(self.changelogFile)

            items = changeLogData.get("nacosChangeLog", None)
            if items:
                includeFiles = []
                for item in items:
                    changeSetObj = item.get("changeSet")
                    includeObj = item.get("include")
                    if changeSetObj:
                        change_set_id = str(changeSetObj["id"])
                        ignore = changeSetObj.get("ignore", False)
                        changeSetObj["ignore"] = ignore
                        if changeSetDict.get(change_set_id) is not None:
                            raise ChangeLogException(
                                f"Repeat change set id {change_set_id}"
                            )

                        changeSetObj["filename"] = changelog_file_name
                        changeSetDict[change_set_id] = changeSetObj
                        changes = changeSetObj["changes"]

                        changeSetChangeDict = {}
                        for change in changes:
                            namespace = change.get("namespace", "")
                            group = change["group"]
                            dataId = change["dataId"]
                            _format = change["format"]
                            patchContent = change.get("patchContent", "")
                            deleteContent = change.get("deleteContent", "")
                            config_key = f"{namespace}/{group}/{dataId}"

                            if changeSetChangeDict.get(config_key) is not None:
                                raise ChangeLogException(
                                    f"Repeated nacos change. changeSetId:{change_set_id}, namespace:{namespace}, group:{group}, dataId:{dataId}"
                                )
                            changeSetChangeDict[config_key] = change

                            if len(patchContent.strip()) > 0:
                                suc, msg = config_validator.validate_content(
                                    patchContent, _format
                                )
                                if not suc:
                                    raise ChangeLogException(
                                        f"PatchContent Invalid!!! changeLogFile: {self.changelogFile}, changeSetId: {change_set_id}, namespace: {namespace}, group: {group}, dataId: {dataId}, format: {_format}. errorMsg: {msg}"
                                    )

                            if len(deleteContent.strip()) > 0:
                                suc, msg = config_validator.validate_content(
                                    deleteContent, _format
                                )
                                if not suc:
                                    raise ChangeLogException(
                                        f"DeleteContent Invalid!!! changeLogFile: {self.changelogFile}, changeSetId: {change_set_id}, namespace: {namespace}, group: {group}, dataId: {dataId}, format: {_format}. errorMsg: {msg}"
                                    )

                        if not ignore:
                            changeSets.append(changeSetObj)

                    elif includeObj:
                        # 引用了其他文件
                        file = includeObj["file"]
                        if file in includeFiles:
                            raise ChangeLogException(
                                f"Repeat include file!!! changeLogFile: {self.changelogFile}, file: {file}"
                            )
                        includeFiles.append(file)
                        childLog = NacosChangeLog(
                            changelogFile=f"{base_dir}/{file}", app=self.app
                        )
                        for change_set_id in childLog.changeSetDict:
                            if change_set_id in changeSetDict:
                                raise ChangeLogException(
                                    f"Repeat change set id: {change_set_id}. Please check your changelog"
                                )
                            else:
                                changeSetDict[change_set_id] = childLog.changeSetDict[
                                    change_set_id
                                ]
                        changeSets.extend(childLog.changeSets)

        elif os.path.isdir(self.changelogFile):
            changelogfiles = []
            for dirpath, dirnames, filenames in os.walk(self.changelogFile):
                for filename in filenames:
                    if filename.endswith((".yaml", ".yml")):
                        changelogfiles.append(os.path.join(dirpath, filename))
            # 根据文件名排序
            sorted_changelogfiles = sorted(changelogfiles, key=extract_version)
            for file in sorted_changelogfiles:
                childLog = NacosChangeLog(changelogFile=file, app=self.app)
                for change_set_id in childLog.changeSetDict:
                    if change_set_id in changeSetDict:
                        raise ChangeLogException(
                            f"Repeat change set id: {change_set_id}. Please check your changelog"
                        )
                    else:
                        changeSetDict[change_set_id] = childLog.changeSetDict[
                            change_set_id
                        ]
                changeSets.extend(childLog.changeSets)

        else:
            raise ChangeLogException(
                f"Changelog file or folder does not exists: {self.changelogFile}"
            )

        self.changeSetDict = changeSetDict
        self.changeSets = changeSets

    def __check_change_log(
        self, changeSetObj, nacos_id: str, contexts: str, variables: dict
    ) -> bool:
        change_set_id = str(changeSetObj["id"])
        # 计算checksum
        checksum = changelog_utils.get_change_set_checksum(
            {"changes": changeSetObj["changes"]}
        )
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
        if log is None:
            log = ConfigOpsChangeLog()
            log.change_set_id = change_set_id
            log.system_type = SystemType.NACOS.value
            log.system_id = nacos_id
            log.exectype = ChangelogExeType.INIT.value
            log.author = changeSetObj.get("author", "")
            log.comment = changeSetObj.get("comment", "")
            log.filename = changeSetObj.get("filename", "")
            # log.contexts = contexts
            log.checksum = checksum
            db.session.add(log)
        elif ChangelogExeType.FAILED.matches(
            log.exectype
        ) or ChangelogExeType.INIT.matches(log.exectype):
            log.checksum = checksum
        else:
            runOnChange = changeSetObj.get("runOnChange", False)
            if runOnChange and log.checksum != checksum:
                log.exectype = ChangelogExeType.INIT.value
                log.checksum = checksum
            else:
                is_execute = False

        _secret = None
        if self.app:
            _secret = get_config(self.app, "config.node.secret")

        if _secret:
            nacos_changes = []
            for change in changeSetObj["changes"]:
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
                    changes=changelog_utils.pack_encrypt_changes(
                        nacos_changes, _secret
                    ),
                )
                db.session.add(log_changes)
            else:
                log_changes.changes = changelog_utils.pack_encrypt_changes(
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
    ):
        """
        获取多个当前需要执行的changeset
        """
        idx = 0
        remoteConfigsCache = {}
        resultChangeConfigDict = {}
        changeSetIds = []
        for changeSetObj in self.changeSets:
            change_set_id = str(changeSetObj["id"])
            # 判断是否在指定的contexts里面
            changeSetCtx = changeSetObj.get("context")
            if not changelog_utils.is_ctx_included(contexts, changeSetCtx):
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
                is_execute = self.__check_change_log(
                    changeSetObj, nacos_id, contexts, vars
                )

            if is_execute:
                logger.info(f"Found change set log: {change_set_id}")

                changeSetIds.append(change_set_id)

                for change in changeSetObj["changes"]:
                    logger.info(f"current change: {change}")
                    namespace = string.Template(change["namespace"]).substitute(vars)
                    group = string.Template(change["group"]).substitute(vars)
                    dataId = string.Template(change["dataId"]).substitute(vars)
                    _format = change["format"]

                    nacosConfig = change.copy()
                    nacosConfig["namespace"] = namespace
                    nacosConfig["group"] = group
                    nacosConfig["dataId"] = dataId
                    nacosConfig["content"] = ""
                    nacosConfig["id"] = ""

                    remote_config, _ = self._get_remote_config(
                        remoteConfigsCache, namespace, group, dataId, client
                    )
                    if remote_config:
                        remote_config_format = remote_config["type"]
                        remote_config_content = remote_config["content"]

                        if remote_config_format != _format:
                            raise ChangeLogException(
                                f"Config format not match. namespace/group/dataId:{namespace}/{group}/{dataId}; changelogFormat:{_format}, nacosFormat:{remote_config_format}"
                            )

                        if len(remote_config_content.strip()) > 0:
                            suc, msg = config_validator.validate_content(
                                remote_config_content, _format
                            )
                            if not suc:
                                raise ChangeLogException(
                                    f"Current Nacos Config Content Invalid!!! namespace: {namespace}, group: {group}, dataId: {dataId}, format: {_format}. errorMsg: {msg}"
                                )

                        nacosConfig["content"] = remote_config_content
                        nacosConfig["id"] = remote_config["id"]

                    configKey = f"{namespace}/{group}/{dataId}"

                    nextContent = nacosConfig.get("content")
                    previousConfig = resultChangeConfigDict.get(configKey)
                    if previousConfig:
                        nextContent = previousConfig["nextContent"]

                    # 直接追加内容，放到 nextContent
                    nextContentRes = config_handler.delete_patch_by_str(
                        nextContent,
                        _format,
                        nacosConfig.get("deleteContent", ""),
                        nacosConfig.get("patchContent", ""),
                    )
                    nacosConfig["nextContent"] = nextContentRes["nextContent"]

                    # 所有patch和delete也聚合在一起
                    if previousConfig:
                        res = config_handler.patch_by_str(
                            previousConfig.get("deleteContent", ""),
                            nacosConfig.get("deleteContent", ""),
                            _format,
                        )
                        nacosConfig["deleteContent"] = res["nextContent"]

                        res = config_handler.patch_by_str(
                            previousConfig.get("patchContent", ""),
                            nacosConfig.get("patchContent", ""),
                            _format,
                        )
                        nacosConfig["patchContent"] = res["nextContent"]

                    resultChangeConfigDict[configKey] = nacosConfig

            idx += 1
            if count > 0 and idx >= count:
                break

        if check_log:
            db.session.commit()
        return changeSetIds, list(resultChangeConfigDict.values())

    def _get_remote_config(
        self, remoteConfigsCache, namespace, group, dataId, client: ConfigOpsNacosClient
    ):
        namespaceGroup = f"{namespace}/{group}"
        remoteConfigs = remoteConfigsCache.get(namespaceGroup)
        if remoteConfigs is None:
            client.namespace = namespace
            resp = client.get_configs(no_snapshot=True, group=group)
            remoteConfigs = resp.get("pageItems")
            remoteConfigsCache[namespaceGroup] = remoteConfigs
        for item in remoteConfigs:
            if item.get("dataId") == dataId:
                return item, remoteConfigs
        return None, remoteConfigs


def apply_change(change_set_id: str, nacos_id: str, func):
    log = (
        db.session.query(ConfigOpsChangeLog)
        .filter_by(
            change_set_id=change_set_id,
            system_id=nacos_id,
            system_type=SystemType.NACOS.value,
        )
        .first()
    )

    if log is None:
        raise ChangeLogException(f"Change log not found. change_set_id:{change_set_id}")

    if ChangelogExeType.EXECUTED.matches(log.exectype):
        raise ChangeLogException(f"Change log executed. change_set_id:{change_set_id}")
    # 执行操作
    try:
        func()
        log.exectype = ChangelogExeType.EXECUTED.value
    except Exception as e:
        log.exectype = ChangelogExeType.FAILED.value
        raise e
    finally:
        db.session.commit()


def apply_changes(change_set_ids, nacos_id: str, func):
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

    # 执行操作
    try:
        func()
        for log in logs:
            log.exectype = ChangelogExeType.EXECUTED.value
    except Exception as e:
        log.exectype = ChangelogExeType.FAILED.value
        raise e
    finally:
        db.session.commit()
