from flask import Flask, jsonify
from flask.json.provider import DefaultJSONProvider
import argparse
import logging
from datetime import datetime
from marshmallow import ValidationError
from configops.api.common import bp as common_bp
from configops.api.nacos import bp as nacos_bp
from configops.api.database import bp as database_bp
from configops.api.elasticsearch import bp as elasticsearch_bp
from configops.api.auth import bp as auth_bp
from configops.api.admin import bp as admin_bp
from configops.api.dashboard import bp as dashboard_bp
from configops.api.auth import init_app as auth_init_app
from configops.config import load_config, get_node_cfg
from configops.utils import constants
from configops.utils.logging_configurator import DefaultLoggingConfigurator
from configops.database import db
from configops.cluster import controller as clueter_controller
from configops.cluster import worker as clueter_worker
from flask_socketio import SocketIO


logger = logging.getLogger(__name__)

error_handler_logger = logging.getLogger("error_handler_logger")

socketio = SocketIO(cors_allowed_origins="*")


class CustomJSONProvider(DefaultJSONProvider):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        return super().default(obj)


def create_app(config_file=None):
    loggingConfig = DefaultLoggingConfigurator()
    loggingConfig.configure_default()
    app = Flask(__name__)

    @app.errorhandler(Exception)
    def handle_exception(error):
        error_handler_logger.error("f Catch global exception {error}", exc_info=True)
        type_name = type(error).__name__
        return f"{type_name}: {str(error)}", 500

    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        error_handler_logger.error("f Catch validation error {error}", exc_info=True)
        return jsonify(error.messages), 400

    config = load_config(config_file)
    if config is not None:
        app.config.update(config)
    loggingConfig.configure_logging(app.config, debug_mode=False)

    node_config = get_node_cfg(app)

    app.json_provider_class = CustomJSONProvider
    app.json = app.json_provider_class(app)

    app.register_blueprint(common_bp)

    if constants.NodeRole.CONTROLLER.matches(node_config["role"]):
        app.register_blueprint(auth_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(dashboard_bp)
    else:
        app.register_blueprint(nacos_bp)
        app.register_blueprint(database_bp)
        app.register_blueprint(elasticsearch_bp)

    db.init(app)
    auth_init_app(app)

    if constants.NodeRole.CONTROLLER.matches(node_config["role"]):
        clueter_controller.register(socketio, app)
    else:
        clueter_worker.register(app)

    socketio.init_app(app)
    return app


if __name__ == "__main__":
    logger.info("Starting flask app")
    parser = argparse.ArgumentParser(description="Run the config-ops application")
    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="服务Host", required=False
    )
    parser.add_argument(
        "--port", type=int, default="5000", help="服务端口", required=False
    )
    parser.add_argument("--debug", help="是否开启Debug模式", required=False)
    parser.add_argument("--config", type=str, help="YAML配置文件", required=False)
    args = parser.parse_args()
    debug = False
    if args.debug:
        debug = True
    app = create_app(config_file=args.config)
    # app.run(host=args.host, port=args.port, debug=debug)
    socketio.run(app, host=args.host, port=args.port, debug=debug)
    logger.info("Started flask app")
