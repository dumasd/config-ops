import logging, requests, base64
from marshmallow import Schema, fields, EXCLUDE
from configops.utils import secret_util
from configops.changelog.elasticsearch_change import ElasticsearchChangelog
from configops.utils.exception import ConfigOpsException, ChangeLogException
from configops.config import get_elasticsearch_cfg
from flask import Blueprint, make_response, request

bp = Blueprint("elasticsearch", __name__)

logger = logging.getLogger(__name__)


class ChangeSetSchema(Schema):
    esId = fields.Str(required=True)
    changeLogFile = fields.Str(required=True)
    count = fields.Int(required=False)
    contexts = fields.Str(required=False)
    vars = fields.Dict()

    class Meta:
        unknown = EXCLUDE


def detect_version_and_create_client(cfg):
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

    for host in hosts:
        headers = {}
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

        response = requests.get(host, headers=headers, verify=False)
        if response.status_code >= 200 or response.status_code <= 299:
            ver = response.json()["version"]["number"]
            logger.info(f"Found Elasticsearch version: {ver}, hosts: {hosts}")
            if ver.startswith("8."):
                from elasticsearch8 import Elasticsearch

                if api_id:
                    secretData = secret_util.get_secret_data(cfg, "app_key")
                    return Elasticsearch(
                        hosts=hosts, api_id=api_id, api_key=secretData.password
                    )
            elif ver.startswith("7."):
                from elasticsearch7 import Elasticsearch
            elif ver.startswith("6."):
                from elasticsearch6 import Elasticsearch
            else:
                raise ConfigOpsException(
                    f"Unsupported Elasticsearch version: {ver}, hosts: {hosts}"
                )

            if credentials_type == 1:
                return Elasticsearch(
                    hosts=hosts,
                    api_id=api_id,
                    api_key=secretData.password,
                    verify_certs=False,
                )
            elif credentials_type == 2:
                return Elasticsearch(
                    hosts=hosts,
                    http_auth=(username, secretData.password),
                    verify_certs=False,
                )
            else:
                return Elasticsearch(hosts=hosts, verify_certs=False)

    raise ConfigOpsException(f"Detect Elasticsearch version fail, hosts: {hosts}")


@bp.route("/elasticsearch/v1/get_change_set", methods=["POST"])
def get_change_set():
    data = ChangeSetSchema().load(request.get_json())
    esId = data.get("esId")
    count = data.get("count", 0)
    contexts = data.get("contexts")
    vars = data.get("vars", {})
    changelogFile = data.get("changeLogFile")

    cfg = get_elasticsearch_cfg(esId)
    if cfg is None:
        return make_response(f"Elasticsearch id not found in config file: {esId}", 404)

    try:
        esChangeLog = ElasticsearchChangelog(changelogFile=changelogFile)
        result = esChangeLog.fetch_multi(esId, count, contexts, vars, True)
        return result
    except ChangeLogException as err:
        logger.error("Elasticsearch changelog invalid.", exc_info=True)
        return make_response(f"Nacos changelog invalid. {str(err)}", 400)


@bp.route("/elasticsearch/v1/apply_change_set", methods=["POST"])
def apply_change_set():
    data = ChangeSetSchema().load(request.get_json())
    esId = data.get("esId")
    count = data.get("count", 0)
    contexts = data.get("contexts")
    vars = data.get("vars", {})
    changelogFile = data.get("changeLogFile")

    cfg = get_elasticsearch_cfg(esId)
    if cfg is None:
        return make_response(f"Elasticsearch id not found in config file: {esId}", 404)
    client = detect_version_and_create_client(cfg)
    try:
        esChangeLog = ElasticsearchChangelog(changelogFile=changelogFile)
        return esChangeLog.apply(client, esId, count, contexts, vars, True)
    except ChangeLogException as err:
        logger.error("Elasticsearch changelog invalid.", exc_info=True)
        return make_response(f"Elasticsearch changelog invalid. {err}", 400)
