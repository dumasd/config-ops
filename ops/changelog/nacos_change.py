import logging
import os
from ops.utils import config_handler, config_validator
from ops.utils.constants import CHANGE_LOG_EXEXTYPE, SYSTEM_TYPE
from ops.utils.exception import ChangeLogException
from ruamel import yaml as ryaml
from jsonschema import Draft7Validator, ValidationError
from ops.utils.nacos_client import ConfigOpsNacosClient
from ops.database.db import db, ConfigOpsChangeLog

logger = logging.getLogger(__name__)

schema = {
    "type": "object",
    "properties": {
        "nacosChangeLog": {
            "type": "array",
            "items": [
                {
                    "type": "object",
                    "properties": {
                        "changeSet": {
                            "type": "object",
                            "properties": {
                                "id": {"type": ["string", "number"]},
                                "author": {"type": "string"},
                                "comment": {"type": "string"},
                                "ignore": {"type": "boolean", "default": "false"},
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
                                "required": ["id", "author", "changes"],
                            },
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
        "required": ["nacosChangeLog"],
    },
}


class NacosChangeLog:
    def __init__(self, changelogFile):
        self.changelogFile = changelogFile
        self.__init_change_log()

    def __append_nacos_config(self, parent, child):
        pass
        # 合并
        format = parent["type"]
        if format != child["type"]:
            raise ChangeLogException(f"Format not equal ")
        patchContent = child["patchContent"]
        deleteContent = child["deleteContent"]

        currentPatchContent = parent["patchContent"]
        currentDeleteContent = parent["deleteContent"]

        if len(patchContent.strip()) > 0:
            if len(currentPatchContent.strip()) > 0:
                _, current, ym = config_handler.parse_content(
                    currentPatchContent, format
                )
                _, patch, _ = config_handler.parse_content(patchContent, format)
                config_handler.patch(patch, current, format)
                parent["patchContent"] = config_handler.to_string(format, current, ym)
            else:
                parent["patchContent"] = patchContent

            if len(deleteContent.strip()) > 0:
                if len(currentDeleteContent.strip()) > 0:
                    _, current, ym = config_handler.parse_content(
                        currentDeleteContent, format
                    )
                    _, patch, _ = config_handler.parse_content(deleteContent, format)
                    config_handler.patch(patch, current, format)
                    parent["deleteContent"] = config_handler.to_string(
                        format, current, ym
                    )
            else:
                parent["deleteContent"] = patchContent

    def __init_change_log(self):
        changeLogData = None
        with open(self.changelogFile, "r") as file:
            try:
                yaml = ryaml.YAML()
                yaml.preserve_quotes = True
                changeLogData = yaml.load(file)
                validator = Draft7Validator(schema)
                validator.validate(changeLogData)
            except ValidationError as e:
                logger.error(f"NacosChangeLog validation error {e}")
                raise

        base_dir = os.path.dirname(self.changelogFile)
        nacosConfigDict = {}
        changeSetDict = {}
        changeSets = []

        items = changeLogData["nacosChangeLog"]
        for item in items:
            # 引用了其他文件
            changeSetObj = item.get("changeSet")
            includeObj = item.get("include")
            if changeSetObj:
                id = str(changeSetObj["id"])
                ignore = changeSetObj.get("ignore", False)
                changeSetObj["ignore"] = ignore
                if changeSetDict.get(id) is not None:
                    raise ChangeLogException(f"Repeat change set id {id}")
                """
                changeSet = {
                    "id": id,
                    "author": author,
                    "comment": comment,
                    "ignore": ignore,
                }
                """
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
                                f"patchContent is not valid. changeSetId:{id}, namespace:{namespace}, group:{group}, dataId:{dataId}, [{format}] type. {msg}"
                            )

                    if len(deleteContent.strip()) > 0:
                        suc, msg = config_validator.validate_content(
                            deleteContent, format
                        )
                        if not suc:
                            raise ChangeLogException(
                                f"deleteContent is not valid. changeSetId:{id}, namespace:{namespace}, group:{group}, dataId:{dataId}, [{format}] type. {msg}"
                            )

                if not ignore:
                    changeSets.append(changeSetObj)

                    """
                    for change in changes:
                        namespace = change.get("namespace", "")
                        group = change["group"]
                        dataId = change["dataId"]
                        format = change["format"]
                        patchContent = change.get("patchContent", "")
                        deleteContent = change.get("deleteContent", "")

                        if len(patchContent.strip()) > 0:
                            suc, msg = config_validator.validate_content(
                                patchContent, format
                            )
                            if not suc:
                                raise ChangeLogException(
                                    f"patchContent is not valid [{format}] type. {msg}"
                                )

                        if len(deleteContent.strip()) > 0:
                            suc, msg = config_validator.validate_content(
                                deleteContent, format
                            )
                            if not suc:
                                raise ChangeLogException(
                                    f"deleteContent is not valid [{format}] type. {msg}"
                                )
                        nacosConfig = {
                            "id": "",
                            "tenant": namespace,
                            "group": group,
                            "dataId": dataId,
                            "type": format,
                            "content": "",
                            "patchContent": patchContent,
                            "deleteContent": deleteContent,
                        }

                        config_key = f"{namespace}/{group}/{dataId}"
                        exists = nacosConfigDict.get(config_key)
                        if exists is None:
                            nacosConfigDict[config_key] = nacosConfig
                        else:
                            self.__append_nacos_config(exists, nacosConfig)
                    """
            elif includeObj:
                file = includeObj["file"]
                childLog = NacosChangeLog(changelogFile=f"{base_dir}/{file}")
                for id in childLog.changeSetDict:
                    if id in changeSetDict:
                        raise ChangeLogException(f"Repeat change set id {id}")
                    else:
                        changeSetDict[id] = childLog.changeSetDict[id]

                changeSets.extend(childLog.changeSets)

                """
                for key in childLog.nacosConfigDict:
                    child = childLog.nacosConfigDict[key]
                    if key in nacosConfigDict:
                        # 合并
                        parent = nacosConfigDict[key]
                        self.__append_nacos_config(parent, child)
                    else:
                        nacosConfigDict[key] = child
                """

            self.nacosConfigDict = nacosConfigDict
            self.changeSetDict = changeSetDict
            self.changeSets = changeSets

    def fetch_current(self, client: ConfigOpsNacosClient, nacos_id: str):
        """
        获取当前需要执行的changeset
        """

        currentChangeSet = None
        for changeSetObj in self.changeSets:
            id = str(changeSetObj["id"])
            log = (
                db.session.query(ConfigOpsChangeLog)
                .filter_by(
                    change_set_id=id,
                    system_id=nacos_id,
                    system_type=SYSTEM_TYPE.NACOS.value,
                )
                .first()
            )
            if (
                log is None
                or CHANGE_LOG_EXEXTYPE.FAILED.matches(log.exectype)
                or CHANGE_LOG_EXEXTYPE.INIT.matches(log.exectype)
            ):
                logger.info(f"Found change set log: {id}")
                currentChangeSet = changeSetObj
                if log is None:
                    log = ConfigOpsChangeLog()
                    log.change_set_id = id
                    log.system_type = SYSTEM_TYPE.NACOS.value
                    log.system_id = nacos_id
                    log.exectype = CHANGE_LOG_EXEXTYPE.INIT.value
                    log.author = changeSetObj.get("author", "")
                    log.comment = changeSetObj.get("comment", "")
                    db.session.add(log)
                    db.session.commit()
                break

        if currentChangeSet is None:
            return None

        resultConfigs = []
        remoteConfigsCache = {}
        changes = currentChangeSet["changes"]
        for change in changes:
            logger.info(f"current change: {change}")
            nacosConfig = change.copy()
            namespace = nacosConfig["namespace"]
            group = nacosConfig["group"]
            dataId = nacosConfig["dataId"]
            format = nacosConfig["format"]
            namespaceGroup = f"{namespace}/{group}"

            remoteConfigs = remoteConfigsCache.get(namespaceGroup)
            if remoteConfigs is None:
                client.namespace = namespace
                resp = client.get_configs(no_snapshot=True, group=group)
                remoteConfigs = resp.get("pageItems")
                remoteConfigsCache[namespaceGroup] = remoteConfigs

            nacosConfig["content"] = ""
            nacosConfig["id"] = ""
            for item in remoteConfigs:
                if item.get("dataId") == dataId:
                    if item["type"] != format:
                        raise ChangeLogException(
                            f"Format does not match. namespace:{namespace}, group:{group}, dataId:{dataId}"
                        )
                    nacosConfig["content"] = item["content"]
                    nacosConfig["id"] = item["id"]
                    break

            # 直接追加内容，放到 nextContent
            delete_res = config_handler.delete_by_str(
                nacosConfig["content"], nacosConfig.get("deleteContent", ""), format
            )
            res = config_handler.patch_by_str(
                delete_res["nextContent"], nacosConfig.get("patchContent", ""), format
            )
            nacosConfig["nextContent"] = res["nextContent"]
            resultConfigs.append(nacosConfig)

        resultChangeSet = currentChangeSet.copy()
        resultChangeSet["changes"] = resultConfigs
        return resultChangeSet

    def fetch_multi(self, client: ConfigOpsNacosClient, nacos_id: str, count=0):
        """
        获取多个当前需要执行的changeset
        """
        idx = 0
        remoteConfigsCache = {}
        resultChangeConfigDict = {}
        changeSetIds = []
        for changeSetObj in self.changeSets:
            id = str(changeSetObj["id"])
            log = (
                db.session.query(ConfigOpsChangeLog)
                .filter_by(
                    change_set_id=id,
                    system_id=nacos_id,
                    system_type=SYSTEM_TYPE.NACOS.value,
                )
                .first()
            )
            if (
                log is None
                or CHANGE_LOG_EXEXTYPE.FAILED.matches(log.exectype)
                or CHANGE_LOG_EXEXTYPE.INIT.matches(log.exectype)
            ):
                logger.info(f"Found change set log: {id}")
                if log is None:
                    log = ConfigOpsChangeLog()
                    log.change_set_id = id
                    log.system_type = SYSTEM_TYPE.NACOS.value
                    log.system_id = nacos_id
                    log.exectype = CHANGE_LOG_EXEXTYPE.INIT.value
                    log.author = changeSetObj.get("author", "")
                    log.comment = changeSetObj.get("comment", "")
                    db.session.add(log)
                    db.session.commit()

                changeSetIds.append(id)

                for change in changeSetObj["changes"]:
                    logger.info(f"current change: {change}")
                    nacosConfig = change.copy()
                    namespace = nacosConfig["namespace"]
                    group = nacosConfig["group"]
                    dataId = nacosConfig["dataId"]
                    format = nacosConfig["format"]

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
            system_type=SYSTEM_TYPE.NACOS.value,
        )
        .first()
    )

    if log is None:
        raise ChangeLogException(f"Change log not found. change_set_id:{change_set_id}")

    if CHANGE_LOG_EXEXTYPE.EXECUTED.matches(log.exectype):
        raise ChangeLogException(f"Change log executed. change_set_id:{change_set_id}")
    # 执行操作
    try:
        func()
        log.exectype = CHANGE_LOG_EXEXTYPE.EXECUTED.value
    except Exception as e:
        log.exectype = CHANGE_LOG_EXEXTYPE.FAILED.value
        raise e
    finally:
        db.session.commit()


def apply_changes(change_set_ids, nacos_id: str, func):
    logs = (
        db.session.query(ConfigOpsChangeLog)
        .filter(
            ConfigOpsChangeLog.change_set_id.in_(change_set_ids),
            ConfigOpsChangeLog.system_id == nacos_id,
            ConfigOpsChangeLog.system_type == SYSTEM_TYPE.NACOS.value,
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
            log.exectype = CHANGE_LOG_EXEXTYPE.EXECUTED.value
    except Exception as e:
        log.exectype = CHANGE_LOG_EXEXTYPE.FAILED.value
        raise e
    finally:
        db.session.commit()
