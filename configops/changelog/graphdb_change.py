# -*- coding: utf-8 -*-
# @Author  : Bruce Wu
# @Time    : 2025/06/10 10:00
import logging, os
from ruamel import yaml as ryaml
from jsonschema import Draft7Validator, ValidationError
from configops.changelog import changelog_utils, graphdb_executor
from configops.utils.constants import (
    ChangelogExeType,
    SystemType,
    extract_version,
    GREMLIN,
    SPARQL,
    OPEN_CYPHER,
)
from configops.database.db import db, ConfigOpsChangeLog, ConfigOpsChangeLogChanges
from configops.utils.exception import ChangeLogException, ConfigOpsException
from configops.config import get_config

logger = logging.getLogger(__name__)

schema = {
    "type": "object",
    "properties": {
        "graphdbChangeLog": {
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
                                                "type": {
                                                    "type": "string",
                                                    "pattern": "^(sparql|gremlin|openCypher)$",
                                                },
                                                "dataset": {
                                                    "type": "string",
                                                    "description": "Dataset for query execution",
                                                },
                                                "query": {"type": "string"},
                                            },
                                            "required": [
                                                "type",
                                                "query",
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
                            "required": ["file"],
                        },
                    },
                },
            ],
        }
    },
    "required": ["graphdbChangeLog"],
}


class GraphdbChangelog:
    def __init__(self, changelog_file=None, app=None):
        self.changelog_file = changelog_file
        self.app = app
        self.__init_change_log__()

    def __init_change_log__(self):
        changeSets = []
        changeSetDict = {}
        if os.path.isfile(self.changelog_file):
            changeLogData = None
            with open(self.changelog_file, "r", encoding="utf-8") as file:
                try:
                    yaml = ryaml.YAML()
                    yaml.preserve_quotes = True
                    changeLogData = yaml.load(file)
                    validator = Draft7Validator(schema)
                    validator.validate(changeLogData)
                except ValidationError as e:
                    raise ChangeLogException(
                        f"Graphdb changelog validation error: {self.changelog_file} \n{e}"
                    )

            base_dir = os.path.dirname(self.changelog_file)
            changelog_file_name = os.path.basename(self.changelog_file)
            changelog_file_id = os.path.splitext(changelog_file_name)[0]
            items = changeLogData.get("graphdbChangeLog", None)

            if items:
                include_files = []
                for item in items:
                    changeSetObj = item.get("changeSet")
                    includeObj = item.get("include")
                    if changeSetObj:
                        change_set_id = str(changeSetObj.get("id", changelog_file_id))
                        changeSetObj["id"] = change_set_id
                        ignore = changeSetObj.get("ignore", False)
                        changeSetObj["ignore"] = ignore
                        if changeSetDict.get(change_set_id):
                            raise ChangeLogException(
                                f"Repeat change set id. changeLogFile: {self.changelog_file}, changeSetId:{change_set_id}"
                            )
                        changeSetObj["filename"] = changelog_file_name
                        changeSetDict[change_set_id] = changeSetObj
                        if not ignore:
                            changeSets.append(changeSetObj)

                    elif includeObj:
                        file = includeObj["file"]
                        if file in include_files:
                            raise ChangeLogException(
                                f"Repeat include file!!! changeLogFile: {self.changelog_file}, file: {file}"
                            )
                        include_files.append(file)
                        childLog = GraphdbChangelog(
                            changelog_file=f"{base_dir}/{file}", app=self.app
                        )
                        for change_set_id in childLog.change_set_dict:
                            if change_set_id in changeSetDict:
                                raise ChangeLogException(
                                    f"Repeat change set id: {change_set_id}. Please check your changelog"
                                )
                            else:
                                changeSetDict[change_set_id] = childLog.change_set_dict[
                                    change_set_id
                                ]
                        changeSets.extend(childLog.change_set_list)

        elif os.path.isdir(self.changelog_file):
            changelogfiles = []
            for dirpath, dirnames, filenames in os.walk(self.changelog_file):
                for filename in filenames:
                    if filename.endswith((".yaml", ".yml")):
                        changelogfiles.append(os.path.join(dirpath, filename))
            # 根据文件名排序
            sorted_changelogfiles = sorted(changelogfiles, key=extract_version)
            for file in sorted_changelogfiles:
                childLog = GraphdbChangelog(changelog_file=file, app=self.app)
                for change_set_id in childLog.change_set_dict:
                    if change_set_id in changeSetDict:
                        raise ChangeLogException(
                            f"Repeat change set id: {change_set_id}. Please check your changelog"
                        )
                    else:
                        changeSetDict[change_set_id] = childLog.change_set_dict[
                            change_set_id
                        ]
                changeSets.extend(childLog.change_set_list)

        else:
            raise ChangeLogException(
                f"Changelog file or folder does not exists: {self.changelog_file}"
            )
        self.change_set_list = changeSets
        self.change_set_dict = changeSetDict

    def __check_change_log__(
        self, change_set_obj, system_id: str, contexts: str, variables: dict
    ) -> bool:
        change_set_id = str(change_set_obj["id"])
        checksum = changelog_utils.get_change_set_checksum_v2(
            change_set_obj["changes"], SystemType.GRAPHDB
        )
        current_filename = change_set_obj["filename"]
        is_execute = True
        log = (
            db.session.query(ConfigOpsChangeLog)
            .filter_by(
                change_set_id=change_set_id,
                system_id=system_id,
                system_type=SystemType.GRAPHDB.value,
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
                    f"This changeSetId is already defined in an earlier changelog. changeSetId:{change_set_id}, Current file:{current_filename}, previous file:{log.filename}"
                )
            if ChangelogExeType.FAILED.matches(
                log.exectype
            ) or ChangelogExeType.INIT.matches(log.exectype):
                log.checksum = checksum
            else:
                runOnChange = change_set_obj.get("runOnChange", False)
                if runOnChange and changelog_utils.is_changeset_changed(log, checksum):
                    log.exectype = ChangelogExeType.INIT.value
                    log.checksum = checksum
                else:
                    log.checksum = checksum
                    is_execute = False
        else:
            log = ConfigOpsChangeLog()
            log.change_set_id = change_set_id
            log.system_type = SystemType.GRAPHDB.value
            log.system_id = system_id
            log.exectype = ChangelogExeType.INIT.value
            log.author = change_set_obj.get("author", "")
            log.comment = change_set_obj.get("comment", "")
            log.filename = change_set_obj.get("filename", "")
            log.checksum = checksum
            db.session.add(log)

        _secret = None
        if self.app:
            _secret = get_config(self.app, "config.node.secret")

        if _secret:
            _changes = []
            for change in change_set_obj["changes"]:
                _change = change.copy()
                _changes.append(_change)
            log_changes = (
                db.session.query(ConfigOpsChangeLogChanges)
                .filter_by(
                    change_set_id=change_set_id,
                    system_id=system_id,
                    system_type=SystemType.GRAPHDB.value,
                )
                .first()
            )
            if log_changes is None:
                log_changes = ConfigOpsChangeLogChanges(
                    change_set_id=change_set_id,
                    system_type=SystemType.GRAPHDB.value,
                    system_id=system_id,
                    changes=changelog_utils.pack_changes(_changes, _secret),
                )
                db.session.add(log_changes)
            else:
                log_changes.changes = changelog_utils.pack_changes(
                    _changes, _secret
                )
        return is_execute

    def fetch_multi(
        self,
        system_id: str,
        count: int = 0,
        contexts: str = None,
        vars: dict = {},
        check_log: bool = True,
    ):
        idx = 0
        final_change_sets = []
        for change_set_obj in self.change_set_list:
            change_set_id = str(change_set_obj["id"])
            # 判断是否在指定的contexts里面
            changeSetCtx = change_set_obj.get("context")
            if not changelog_utils.is_ctx_included(contexts, changeSetCtx):
                continue

            is_execute = True

            if check_log:
                is_execute = self.__check_change_log__(
                    change_set_obj, system_id, contexts, vars
                )

            if is_execute:
                logger.info(f"Found change set log: {change_set_id}")
                final_change_set = change_set_obj.copy()
                final_change_sets.append(final_change_set)

            idx += 1
            if count > 0 and idx >= count:
                break

        if check_log:
            db.session.commit()

        return final_change_sets

    def apply(
        self,
        system_cfg,
        system_id: str,
        count: int = 0,
        contexts: str = None,
        vars: dict = {},
        check_log: bool = True,
    ):
        change_sets = self.fetch_multi(system_id, count, contexts, vars, check_log)
        if len(change_sets) == 0:
            return []
        for change_set in change_sets:
            change_set_id = str(change_set["id"])
            changelog_filename = change_set["filename"]
            try:
                changes = change_set["changes"]
                log = None
                if check_log:
                    log = (
                        db.session.query(ConfigOpsChangeLog)
                        .filter_by(
                            change_set_id=change_set_id,
                            system_id=system_id,
                            system_type=SystemType.GRAPHDB.value,
                        )
                        .first()
                    )
                executor = graphdb_executor.get_executor(system_cfg["dialect"])
                for change in changes:
                    _type = change["type"]
                    _querys = [change["query"]]
                    _dataset = change.get("dataset", None)
                    try:
                        if _type == SPARQL:
                            executor.execute_sparql(
                                system_cfg, _querys, dataset=_dataset
                            )
                        elif _type == GREMLIN:
                            executor.execute_gremlin(
                                system_cfg, _querys, dataset=_dataset
                            )
                        elif _type == OPEN_CYPHER:
                            executor.execute_opencypher(
                                system_cfg, _querys, dataset=_dataset
                            )
                    except Exception as e:
                        logger.error(
                            f"Run graphdb script error. changeSetId: {change_set_id}, type: {_type}. {e}",
                            exc_info=True,
                        )
                        raise ConfigOpsException(
                            f"Run graphdb script error. changelogFile:{changelog_filename}, changeSetId: {change_set_id}, type: {_type}, message: {e}"
                        )
                if log:
                    log.exectype = ChangelogExeType.EXECUTED.value
            except Exception as e:
                if log:
                    log.exectype = ChangelogExeType.FAILED.value
                raise
            finally:
                db.session.commit()
