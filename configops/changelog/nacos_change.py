import logging, os, string
from configops.changelog import changelog_utils
from configops.utils import config_handler, config_validator
from configops.utils.constants import ChangelogExeType, SystemType, extract_version
from configops.utils.exception import ChangeLogException
from ruamel import yaml as ryaml
from jsonschema import Draft7Validator, ValidationError
from configops.utils.nacos_client import ConfigOpsNacosClient
from configops.database.db import db, ConfigOpsChangeLog

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
    def __init__(self, changelogFile=None):
        self.changelogFile = changelogFile
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
                        id = str(changeSetObj["id"])
                        ignore = changeSetObj.get("ignore", False)
                        changeSetObj["ignore"] = ignore
                        if changeSetDict.get(id) is not None:
                            raise ChangeLogException(f"Repeat change set id {id}")

                        changeSetObj["filename"] = changelog_file_name
                        changeSetDict[id] = changeSetObj
                        changes = changeSetObj["changes"]

                        changeSetChangeDict = {}
                        for change in changes:
                            namespace = change.get("namespace", "")
                            group = change["group"]
                            dataId = change["dataId"]
                            format = change["format"]
                            patchContent = change.get("patchContent", "")
                            deleteContent = change.get("deleteContent", "")
                            config_key = f"{namespace}/{group}/{dataId}"

                            if changeSetChangeDict.get(config_key) is not None:
                                raise ChangeLogException(
                                    f"Repeated nacos change. changeSetId:{id}, namespace:{namespace}, group:{group}, dataId:{dataId}"
                                )
                            changeSetChangeDict[config_key] = change

                            if len(patchContent.strip()) > 0:
                                suc, msg = config_validator.validate_content(
                                    patchContent, format
                                )
                                if not suc:
                                    raise ChangeLogException(
                                        f"PatchContent Invalid!!! changeLogFile: {self.changelogFile}, changeSetId: {id}, namespace: {namespace}, group: {group}, dataId: {dataId}, format: {format}. errorMsg: {msg}"
                                    )

                            if len(deleteContent.strip()) > 0:
                                suc, msg = config_validator.validate_content(
                                    deleteContent, format
                                )
                                if not suc:
                                    raise ChangeLogException(
                                        f"DeleteContent Invalid!!! changeLogFile: {self.changelogFile}, changeSetId: {id}, namespace: {namespace}, group: {group}, dataId: {dataId}, format: {format}. errorMsg: {msg}"
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
                        childLog = NacosChangeLog(changelogFile=f"{base_dir}/{file}")
                        for id in childLog.changeSetDict:
                            if id in changeSetDict:
                                raise ChangeLogException(
                                    f"Repeat change set id: {id}. Please check your changelog"
                                )
                            else:
                                changeSetDict[id] = childLog.changeSetDict[id]
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
                childLog = NacosChangeLog(changelogFile=file)
                for id in childLog.changeSetDict:
                    if id in changeSetDict:
                        raise ChangeLogException(
                            f"Repeat change set id: {id}. Please check your changelog"
                        )
                    else:
                        changeSetDict[id] = childLog.changeSetDict[id]
                changeSets.extend(childLog.changeSets)

        else:
            raise ChangeLogException(
                f"Changelog file or folder does not exists: {self.changelogFile}"
            )

        self.changeSetDict = changeSetDict
        self.changeSets = changeSets

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
            id = str(changeSetObj["id"])
            # 判断是否在指定的contexts里面
            changeSetCtx = changeSetObj.get("context")
            if not changelog_utils.is_ctx_included(contexts, changeSetCtx):
                continue

            # 计算checksum
            checksum = changelog_utils.get_change_set_checksum(
                {"changes": changeSetObj["changes"]}
            )

            is_execute = True
            if (
                spec_changesets
                and len(spec_changesets) > 0
                and id not in spec_changesets
            ):
                is_execute = False

            # 查询log
            if check_log:
                log = (
                    db.session.query(ConfigOpsChangeLog)
                    .filter_by(
                        change_set_id=id,
                        system_id=nacos_id,
                        system_type=SystemType.NACOS.value,
                    )
                    .first()
                )
                if log is None:
                    log = ConfigOpsChangeLog()
                    log.change_set_id = id
                    log.system_type = SystemType.NACOS.value
                    log.system_id = nacos_id
                    log.exectype = ChangelogExeType.INIT.value
                    log.author = changeSetObj.get("author", "")
                    log.comment = changeSetObj.get("comment", "")
                    log.filename = changeSetObj.get("filename", "")
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

            if is_execute:
                logger.info(f"Found change set log: {id}")

                changeSetIds.append(id)

                for change in changeSetObj["changes"]:
                    logger.info(f"current change: {change}")

                    namespaceTemplate = string.Template(change["namespace"])
                    namespace = namespaceTemplate.substitute(vars)

                    groupTemplate = string.Template(change["group"])
                    group = groupTemplate.substitute(vars)

                    dataIdTemplate = string.Template(change["dataId"])
                    dataId = dataIdTemplate.substitute(vars)

                    format = change["format"]

                    nacosConfig = change.copy()
                    nacosConfig["namespace"] = namespace
                    nacosConfig["group"] = group
                    nacosConfig["dataId"] = dataId
                    nacosConfig["content"] = ""
                    nacosConfig["id"] = ""

                    remoteConfig, _ = self._get_remote_config(
                        remoteConfigsCache, namespace, group, dataId, client
                    )
                    if remoteConfig:
                        if remoteConfig["type"] != format:
                            raise ChangeLogException(
                                f"Format does not match. namespace:{namespace}, group:{group}, dataId:{dataId}"
                            )
                        nacosConfig["content"] = remoteConfig["content"]
                        nacosConfig["id"] = remoteConfig["id"]

                    configKey = f"{namespace}/{group}/{dataId}"

                    nextContent = nacosConfig.get("content")
                    previousConfig = resultChangeConfigDict.get(configKey)
                    if previousConfig:
                        nextContent = previousConfig["nextContent"]

                    # 直接追加内容，放到 nextContent
                    nextContentRes = config_handler.delete_patch_by_str(
                        nextContent,
                        format,
                        nacosConfig.get("deleteContent", ""),
                        nacosConfig.get("patchContent", ""),
                    )
                    nacosConfig["nextContent"] = nextContentRes["nextContent"]

                    # 所有patch和delete也聚合在一起
                    if previousConfig:
                        res = config_handler.patch_by_str(
                            previousConfig.get("deleteContent", ""),
                            nacosConfig.get("deleteContent", ""),
                            format,
                        )
                        nacosConfig["deleteContent"] = res["nextContent"]

                        res = config_handler.patch_by_str(
                            previousConfig.get("patchContent", ""),
                            nacosConfig.get("patchContent", ""),
                            format,
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
