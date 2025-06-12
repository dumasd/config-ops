import logging, os
from marshmallow import Schema, fields, EXCLUDE
from configops.changelog.graphdb_change import GraphdbChangelog
from configops.utils.exception import ChangeLogException
from configops.config import get_graphdb_cfg
from flask import Blueprint, make_response, request, current_app

bp = Blueprint("graphdb", __name__, url_prefix=os.getenv("FLASK_APPLICATION_ROOT", "/"))

logger = logging.getLogger(__name__)


class ChangeSetSchema(Schema):
    systemId = fields.Str(required=True)
    changeLogFile = fields.Str(required=True)
    count = fields.Int(required=False)
    contexts = fields.Str(required=False)
    vars = fields.Dict()

    class Meta:
        unknown = EXCLUDE


@bp.route("/graphdb/v1/apply_change_set", methods=["POST"])
def apply_change_set():
    data = ChangeSetSchema().load(request.get_json())
    system_id = data.get("systemId")
    count = data.get("count", 0)
    contexts = data.get("contexts")
    variables = data.get("vars", {})
    changelogFile = data.get("changeLogFile")

    cfg = get_graphdb_cfg(system_id)
    if cfg is None:
        return make_response(f"Graphdb id not found in config file: {system_id}", 404)
    try:
        graphdb_changelog = GraphdbChangelog(
            changelog_file=changelogFile, app=current_app
        )
        graphdb_changelog.apply(cfg, system_id, count, contexts, variables, True)
        return "OK"
    except ChangeLogException as err:
        logger.error("Graphdb changelog invalid.", exc_info=True)
        return make_response(f"Graphdb changelog invalid. {str(err)}", 400)
