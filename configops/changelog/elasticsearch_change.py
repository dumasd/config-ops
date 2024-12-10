import logging, os, string, base64, requests, urllib
import urllib.parse
from ruamel import yaml as ryaml
from jsonschema import Draft7Validator, ValidationError
from configops.changelog import changelog_utils
from configops.utils import config_validator, secret_util
from configops.utils.constants import CHANGE_LOG_EXEXTYPE, SYSTEM_TYPE, extract_version
from configops.database.db import db, ConfigOpsChangeLog
from configops.utils.exception import ChangeLogException, ConfigOpsException

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
    def __init__(self, changelogFile=None):
        self.changelogFile = changelogFile
        self.__init_change_log()

    def __init_change_log(self):
        changeSets = []
        changeSetDict = {}
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
                        f"Elasticsearch changelog validation error: {self.changelogFile} \n{e}"
                    )

            base_dir = os.path.dirname(self.changelogFile)
            items = changeLogData.get("elasticsearchChangeLog", None)

            if items:
                for item in items:
                    changeSetObj = item.get("changeSet")
                    includeObj = item.get("include")
                    if changeSetObj:
                        id = str(changeSetObj["id"])
                        ignore = changeSetObj.get("ignore", False)
                        changeSetObj["ignore"] = ignore
                        if changeSetDict.get(id):
                            raise ChangeLogException(f"Repeat change set id {id}")
                        changeSetDict[id] = changeSetObj
                        changes = changeSetObj["changes"]
                        for change in changes:
                            method = change.get("method")
                            path = change.get("path")
                            body = change.get("body")
                            if body:
                                suc, _ = config_validator.validate_json(body)
                                if not suc:
                                    raise ChangeLogException(
                                        f"Body is not json. changeSetId:{id}, method:{method}, path:{path}, body:{body}"
                                    )
                        if not ignore:
                            changeSets.append(changeSetObj)

                    elif includeObj:
                        file = includeObj["file"]
                        childLog = ElasticsearchChangelog(
                            changelogFile=f"{base_dir}/{file}"
                        )
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
                childLog = ElasticsearchChangelog(changelogFile=file)
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
        self.changeSets = changeSets
        self.changeSetDict = changeSetDict

    def fetch_multi(
        self,
        elasticsearch_id: str,
        count: int = 0,
        contexts: str = None,
        vars: dict = {},
        check_log: bool = True,
    ):
        idx = 0
        finalChangeSets = []
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

            if check_log:
                log = (
                    db.session.query(ConfigOpsChangeLog)
                    .filter_by(
                        change_set_id=id,
                        system_id=elasticsearch_id,
                        system_type=SYSTEM_TYPE.ELASTICSEARCH.value,
                    )
                    .first()
                )
                if log is None:
                    log = ConfigOpsChangeLog()
                    log.change_set_id = id
                    log.system_type = SYSTEM_TYPE.ELASTICSEARCH.value
                    log.system_id = elasticsearch_id
                    log.exectype = CHANGE_LOG_EXEXTYPE.INIT.value
                    log.author = changeSetObj.get("author", "")
                    log.comment = changeSetObj.get("comment", "")
                    log.checksum = checksum
                    db.session.add(log)
                elif CHANGE_LOG_EXEXTYPE.FAILED.matches(
                    log.exectype
                ) or CHANGE_LOG_EXEXTYPE.INIT.matches(log.exectype):
                    log.checksum = checksum
                else:
                    runOnChange = changeSetObj.get("runOnChange", False)
                    if runOnChange and log.checksum != checksum:
                        log.exectype = CHANGE_LOG_EXEXTYPE.INIT.value
                        log.checksum = checksum
                    else:
                        is_execute = False

            if is_execute:
                logger.info(f"Found change set log: {id}")
                finalChangeSet = changeSetObj.copy()
                for change in finalChangeSet["changes"]:
                    pathTemplate = string.Template(change["path"])
                    path = pathTemplate.substitute(vars)
                    change["path"] = path
                finalChangeSets.append(finalChangeSet)

            idx += 1
            if count > 0 and idx >= count:
                break

        if check_log:
            db.session.commit()

        return finalChangeSets

    def __request(self, cfg, method, path, body):
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
                id = str(changeSet["id"])
                changes = changeSet["changes"]
                log = None
                if check_log:
                    log = (
                        db.session.query(ConfigOpsChangeLog)
                        .filter_by(
                            change_set_id=id,
                            system_id=elasticsearch_id,
                            system_type=SYSTEM_TYPE.ELASTICSEARCH.value,
                        )
                        .first()
                    )
                for change in changes:
                    path = change["path"]
                    method = change["method"]
                    body = change.get("body")
                    try:
                        resp = self.__request(
                            es_cfg, method=method, path=path, body=body
                        )
                        # resp = es_client.transport.perform_request(
                        #     url=path,
                        #     method=method,
                        #     body=body,
                        #     headers={"Content-Type": "application/json"},
                        # )
                        change["success"] = True
                        change["message"] = f"{resp.text}"
                    except Exception as e:
                        logger.error(
                            f"Execute elastic request error. changeSetId: {id}, path: {path}, method: {method}. {e}",
                            exc_info=True,
                        )
                        change["success"] = False
                        change["message"] = f"{e}"
                        raise ConfigOpsException(
                            f"Execute elastic request error. changeSetId: {id}, path: {path}, method: {method}. {e}"
                        )
                if log:
                    log.exectype = CHANGE_LOG_EXEXTYPE.EXECUTED.value
            except ConfigOpsException as e:
                if log:
                    log.exectype = CHANGE_LOG_EXEXTYPE.FAILED.value
            finally:
                db.session.commit()
        return changeSets
