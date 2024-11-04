from flask import Flask
import argparse
import logging
from configops.api.nacos import bp as nacos_bp
from configops.api.database import bp as database_bp
from configops.api.common import bp as common_bp
from configops.config import load_config
from configops.utils.logging_configurator import DefaultLoggingConfigurator
from configops.database import db

logger = logging.getLogger(__name__)

error_handler_logger = logging.getLogger("error_handler_logger")


def create_app(config_file=None):
    loggingConfig = DefaultLoggingConfigurator()
    loggingConfig.configure_default()
    app = Flask(__name__)

    @app.errorhandler(Exception)
    def handle_exception(error):
        error_handler_logger.error("f Catch exception {error}", exc_info=True)
        type_name = type(error).__name__
        return f"{type_name}: {error}", 500

    app.register_blueprint(database_bp)
    app.register_blueprint(nacos_bp)
    app.register_blueprint(common_bp)
    config = load_config(config_file)
    if config is not None:
        app.config.update(config)
    loggingConfig.configure_logging(app.config, debug_mode=False)
    db.init(app)

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
    app.run(host=args.host, port=args.port, debug=debug)

    logger.info("Started flask app")
