import logging, os, string, base64, requests, urllib
import urllib.parse
from ruamel import yaml as ryaml
from jsonschema import Draft7Validator, ValidationError
from configops.changelog import changelog_utils
from configops.utils import config_validator, secret_util
from configops.utils.constants import ChangelogExeType, SystemType, extract_version
from configops.database.db import db, ConfigOpsChangeLog, ConfigOpsChangeLogChanges
from configops.utils.exception import ChangeLogException, ConfigOpsException
from configops.config import get_config

logger = logging.getLogger(__name__)
schema = {
    "type": "object",
    "properties": {
        "elasticsearchChangeLog": {
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
                                                "method": {
                                                    "type": "string",
                                                    "pattern": "^(GET|PUT|POST|DELETE|HEAD|PATCH|OPTIONS)$",
                                                },
                                                "path": {"type": "string"},
                                                "body": {"type": "string"},
                                            },
                                            "required": [
                                                "method",
                                                "path",
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
                            "required": ["file"],
                        },
                    },
                },
            ],
        }
    },
    "required": ["elasticsearchChangeLog"],
}


class ElasticsearchChangelog:
    def __init__(self, changelog_file=None, app=None):
        self.changelog_file = changelog_file
        self.app = app
        self.__init_change_log()

    def __init_change_log(self):
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
                        f"Elasticsearch changelog validation error: {self.changelog_file} \n{e}"
                    )

            changelog_file_name = os.path.basename(self.changelog_file)
            items = changeLogData.get("elasticsearchChangeLog", None)

            if items:
                include_files = []
                for item in items:
                    changeSetObj = item.get("changeSet")
                    includeObj = item.get("include")
                    if changeSetObj:
                        change_set_id = str(changeSetObj["id"])
                        ignore = changeSetObj.get("ignore", False)
                        changeSetObj["ignore"] = ignore
                        if changeSetDict.get(change_set_id):
                            raise ChangeLogException(
                                f"Repeat change set id {change_set_id}"
                            )
                        changeSetObj["filename"] = changelog_file_name
                        changeSetDict[change_set_id] = changeSetObj
                        changes = changeSetObj["changes"]
                        for change in changes:
                            method = change.get("method")
                            path = change.get("path")
                            body = change.get("body")
                            if body:
                                suc, _ = config_validator.validate_json(body)
                                if not suc:
                                    raise ChangeLogException(
                                        f"Body is not json. changeSetId:{change_set_id}, method:{method}, path:{path}, body:{body}"
                                    )
                        if not ignore:
                            changeSets.append(changeSetObj)

                    elif includeObj:
                        file = includeObj["file"]
                        if file in include_files:
                            raise ChangeLogException(
                                f"Repeat include file!!! changeLogFile: {self.changelog_file}, file: {file}"
                            )
                        include_files.append(file)
                        childLog = ElasticsearchChangelog(
                            changelog_file=file, app=self.app
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
                childLog = ElasticsearchChangelog(changelog_file=file, app=self.app)
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

    def __check_change_log(
        self, change_set_obj, elasticsearch_id: str, contexts: str, variables: dict
    ) -> bool:
        change_set_id = str(change_set_obj["id"])
        checksum = changelog_utils.get_change_set_checksum(
            {"changes": change_set_obj["changes"]}
        )
        current_filename = change_set_obj["filename"]
        is_execute = True
        log = (
            db.session.query(ConfigOpsChangeLog)
            .filter_by(
                change_set_id=change_set_id,
                system_id=elasticsearch_id,
                system_type=SystemType.ELASTICSEARCH.value,
            )
            .first()
        )
        if log is not None:
            if log.filename != current_filename:
                raise ChangeLogException(
                    f"This changeSetId is already defined in an earlier changelog file. changeSetId:{change_set_id}, Current file:{current_filename}, previous file:{log.filename}"
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
            log.system_type = SystemType.ELASTICSEARCH.value
            log.system_id = elasticsearch_id
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
            elasicsearch_changes = []
            for change in change_set_obj["changes"]:
                elasicsearch_change = change.copy()
                elasicsearch_change["path"] = string.Template(
                    change["path"]
                ).substitute(variables)
                elasicsearch_changes.append(elasicsearch_change)
            log_changes = (
                db.session.query(ConfigOpsChangeLogChanges)
                .filter_by(
                    change_set_id=change_set_id,
                    system_id=elasticsearch_id,
                    system_type=SystemType.ELASTICSEARCH.value,
                )
                .first()
            )
            if log_changes is None:
                log_changes = ConfigOpsChangeLogChanges(
                    change_set_id=change_set_id,
                    system_type=SystemType.ELASTICSEARCH.value,
                    system_id=elasticsearch_id,
                    changes=changelog_utils.pack_encrypt_changes(
                        elasicsearch_changes, _secret
                    ),
                )
                db.session.add(log_changes)
            else:
                log_changes.changes = changelog_utils.pack_encrypt_changes(
                    elasicsearch_changes, _secret
                )
        return is_execute

    def fetch_multi(
        self,
        elasticsearch_id: str,
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
                is_execute = self.__check_change_log(
                    change_set_obj, elasticsearch_id, contexts, vars
                )

            if is_execute:
                logger.info(f"Found change set log: {change_set_id}")
                final_change_set = change_set_obj.copy()
                for change in final_change_set["changes"]:
                    change["path"] = string.Template(change["path"]).substitute(vars)
                final_change_sets.append(final_change_set)

            idx += 1
            if count > 0 and idx >= count:
                break

        if check_log:
            db.session.commit()

        return final_change_sets

    def __request(self, cfg, method, path, data):
        url = cfg.get("url")
        hosts = url.split(",")

        username = cfg.get("username")
        password = cfg.get("password")
        api_id = cfg.get("api_id")
        api_key = cfg.get("api_key")

        credentials_type = None
        if api_id:
            credentials_type = 1
            secretData = secret_util.get_secret_data(cfg, "app_key")
            api_key = secretData.password
        elif username:
            credentials_type = 2
            secretData = secret_util.get_secret_data(cfg, "password")
            password = secretData.password

        errorResponse = None
        for host in hosts:
            headers = {"Content-Type": "application/json"}
            if credentials_type == 1:
                encoded_key = base64.b64encode(
                    f"{api_id}:{api_key}".encode("utf-8")
                ).decode("utf-8")
                headers["Authorization"] = f"ApiKey {encoded_key}"
            elif credentials_type == 2:
                encoded_key = base64.b64encode(
                    f"{username}:{password}".encode("utf-8")
                ).decode("utf-8")
                headers["Authorization"] = f"Basic {encoded_key}"

            response = requests.request(
                method=method,
                data=data,
                url=urllib.parse.urljoin(host, path),
                headers=headers,
                verify=False,
            )
            if response.status_code >= 200 and response.status_code < 300:
                # 处理成功
                return response
            else:
                errorResponse = response

        raise ConfigOpsException(
            f"status_code: {errorResponse.status_code} , text: {errorResponse.text}"
        )

    def apply(
        self,
        es_cfg,
        elasticsearch_id: str,
        count: int = 0,
        contexts: str = None,
        vars: dict = {},
        check_log: bool = True,
    ):
        changeSets = self.fetch_multi(
            elasticsearch_id, count, contexts, vars, check_log
        )
        if len(changeSets) == 0:
            return []

        for changeSet in changeSets:
            try:
                change_set_id = str(changeSet["id"])
                changes = changeSet["changes"]
                log = None
                if check_log:
                    log = (
                        db.session.query(ConfigOpsChangeLog)
                        .filter_by(
                            change_set_id=change_set_id,
                            system_id=elasticsearch_id,
                            system_type=SystemType.ELASTICSEARCH.value,
                        )
                        .first()
                    )
                for change in changes:
                    path = change["path"]
                    method = change["method"]
                    body = change.get("body")
                    try:
                        data = None
                        if body:
                            data = body.encode("utf-8")
                        resp = self.__request(
                            es_cfg, method=method, path=path, data=data
                        )
                        change["success"] = True
                        change["message"] = f"{resp.text}"
                    except Exception as e:
                        logger.error(
                            f"Execute elastic request error. changeSetId: {change_set_id}, path: {path}, method: {method}. {e}",
                            exc_info=True,
                        )
                        change["success"] = False
                        change["message"] = str(e)
                        raise ConfigOpsException(str(e))
                if log:
                    log.exectype = ChangelogExeType.EXECUTED.value
            except ConfigOpsException as e:
                if log:
                    log.exectype = ChangelogExeType.FAILED.value
            finally:
                db.session.commit()
        return changeSets
