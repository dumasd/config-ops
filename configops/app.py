import os
import argparse
import logging
from flask import Flask, jsonify
from flask.json.provider import DefaultJSONProvider
from flask_compress import Compress
from flask_caching import Cache
from flask_socketio import SocketIO
from datetime import datetime, timedelta
from marshmallow import ValidationError
from configops.api.common import bp as common_bp
from configops.api.nacos import bp as nacos_bp
from configops.api.database import bp as database_bp
from configops.api.elasticsearch import bp as elasticsearch_bp
from configops.api.graphdb import bp as graphdb_bp
from configops.api.auth import bp as auth_bp
from configops.api.admin import bp as admin_bp
from configops.api.dashboard import bp as dashboard_bp
from configops.api.web import bp as web_bp
from configops.api.auth import init_app as auth_init_app
from configops.config import load_config, get_node_cfg
from configops.utils import constants
from configops.utils.logging_configurator import DefaultLoggingConfigurator
from configops.database import db
from configops.cluster import controller as clueter_controller
from configops.cluster import worker as clueter_worker


logger = logging.getLogger(__name__)

error_handler_logger = logging.getLogger("error_handler_logger")


def __get_socketio_path():
    application_root = os.getenv("FLASK_APPLICATION_ROOT", "/")
    if application_root != "/":
        return f"{application_root}.socket.io"
    else:
        return "/socket.io"


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
        error_handler_logger.error(f"Catch global exception {error}", exc_info=True)
        type_name = type(error).__name__
        return f"{type_name}: {str(error)}", 500

    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        error_handler_logger.error(f"Catch validation error {error}", exc_info=True)
        return jsonify(error.messages), 400

    config = load_config(config_file)
    if config is not None:
        app.config.update(config)
    loggingConfig.configure_logging(app.config, debug_mode=False)

    node_config = get_node_cfg(app)

    app.json_provider_class = CustomJSONProvider
    app.json = app.json_provider_class(app)

    # Static resources cache
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = timedelta(days=90)
    if constants.NodeRole.CONTROLLER.matches(node_config["role"]):
        app.config["COMPRESS_MIMETYPES"] = [
            "text/html",
            "text/css",
            "text/xml",
            "text/javascript",
            "application/javascript",
            "application/xml",
            "application/x-font-ttf",
            "application/x-font-opentype",
            "application/x-font-truetype",
            "image/svg+xml",
            "image/x-icon",
            "font/ttf",
            "font/eot",
            "font/otf",
            "font/opentype",
        ]
        app.config["COMPRESS_ALGORITHM"] = "gzip"
        app.config["COMPRESS_LEVEL"] = 6
        app.config["COMPRESS_MIN_SIZE"] = 512
        cache = Cache(
            config={
                "CACHE_TYPE": "SimpleCache",
                "CACHE_DEFAULT_TIMEOUT": 30 * 24 * 60 * 60,
            }
        )
        cache.init_app(app)
        compress = Compress()
        compress.init_app(app)
        compress.cache = cache
        compress.cache_key = lambda request: request.url

    app.register_blueprint(common_bp)

    if constants.NodeRole.CONTROLLER.matches(node_config["role"]):
        app.register_blueprint(auth_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(dashboard_bp)
        app.register_blueprint(web_bp)
    else:
        app.register_blueprint(nacos_bp)
        app.register_blueprint(database_bp)
        app.register_blueprint(elasticsearch_bp)
        app.register_blueprint(graphdb_bp)

    db.init(app, node_config)
    auth_init_app(app)

    if constants.NodeRole.CONTROLLER.matches(node_config["role"]):
        socketio = SocketIO(
            cors_allowed_origins="*",
            path=__get_socketio_path(),
            max_http_buffer_size=50 * 1024 * 1024,
        )
        app.config[constants.CONTROLLER_SOCKETIO] = socketio
        clueter_controller.register(socketio, app)
        socketio.init_app(app)
    else:
        clueter_worker.register(app)

    logger.info(f"Flask static folder: {app.static_folder}")
    return app


if __name__ == "__main__":
    logger.info("Starting flask app")
    parser = argparse.ArgumentParser(description="Run the config-ops application")
    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="Server Host", required=False
    )
    parser.add_argument(
        "--port", type=int, default="5000", help="Server Port", required=False
    )
    parser.add_argument("--debug", help="Debug mode", required=False)
    parser.add_argument("--config", type=str, help="YAML config file", required=False)
    args = parser.parse_args()
    debug = True if args.debug else False

    app = create_app(config_file=args.config)
    socketio = app.config.get(constants.CONTROLLER_SOCKETIO)

    if socketio:
        socketio.run(app, host=args.host, port=args.port, debug=debug)
    else:
        app.run(host=args.host, port=args.port, debug=debug)
    logger.info("Started flask app")
