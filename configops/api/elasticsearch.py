# -*- coding: utf-8 -*-
# @Author  : Bruce Wu
import logging, os
from marshmallow import Schema, fields, EXCLUDE
from configops.changelog.elasticsearch_change import ElasticsearchChangelog
from configops.utils.exception import ConfigOpsException, ChangeLogException
from configops.config import get_elasticsearch_cfg
from flask import Blueprint, make_response, request

bp = Blueprint(
    "elasticsearch", __name__, url_prefix=os.getenv("FLASK_APPLICATION_ROOT", "/")
)

logger = logging.getLogger(__name__)


class ChangeSetSchema(Schema):
    esId = fields.Str(required=True)
    changeLogFile = fields.Str(required=True)
    count = fields.Int(required=False)
    contexts = fields.Str(required=False)
    vars = fields.Dict()

    class Meta:
        unknown = EXCLUDE


@bp.route("/elasticsearch/v1/get_change_set", methods=["POST"])
def get_change_set():
    data = ChangeSetSchema().load(request.get_json())
    esId = data.get("esId")
    count = data.get("count", 0)
    contexts = data.get("contexts")
    variables = data.get("vars", {})
    changelogFile = data.get("changeLogFile")

    cfg = get_elasticsearch_cfg(esId)
    if cfg is None:
        return make_response(f"Elasticsearch id not found in config file: {esId}", 404)

    try:
        esChangeLog = ElasticsearchChangelog(changelogFile=changelogFile)
        result = esChangeLog.fetch_multi(esId, count, contexts, variables, True)
        return result
    except ChangeLogException as err:
        logger.error("Elasticsearch changelog invalid.", exc_info=True)
        return make_response(f"Elasticsearch changelog invalid. {str(err)}", 400)


@bp.route("/elasticsearch/v1/apply_change_set", methods=["POST"])
def apply_change_set():
    data = ChangeSetSchema().load(request.get_json())
    esId = data.get("esId")
    count = data.get("count", 0)
    contexts = data.get("contexts")
    variables = data.get("vars", {})
    changelogFile = data.get("changeLogFile")

    cfg = get_elasticsearch_cfg(esId)
    if cfg is None:
        return make_response(f"Elasticsearch id not found in config file: {esId}", 404)
    try:
        esChangeLog = ElasticsearchChangelog(changelogFile=changelogFile)
        return esChangeLog.apply(cfg, esId, count, contexts, variables, True)
    except ChangeLogException as err:
        logger.error("Elasticsearch changelog invalid.", exc_info=True)
        return make_response(f"Elasticsearch changelog invalid. {str(err)}", 400)
