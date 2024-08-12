from flask import Flask
import argparse
import logging
from ops.api.nacos import bp as nacos_bp
from ops.api.database import bp as database_bp
from ops.config import load_config
from ops.utils.logging_configurator import DefaultLoggingConfigurator

logger = logging.getLogger(__name__)


def create_app(config_file="config.yaml") -> Flask:
    app = Flask(__name__)
    app.register_blueprint(database_bp)
    app.register_blueprint(nacos_bp)
    config = load_config(config_file)
    app.config.update(config)
    loggingConfig = DefaultLoggingConfigurator()
    loggingConfig.configure_logging(config, debug_mode=False)
    return app


if __name__ == "__main__":
    logger.info("Starting flask app")
    parser = argparse.ArgumentParser(description="Run the config-ops application")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="服务Host")
    parser.add_argument("--port", type=int, default="5000", help="服务端口")
    parser.add_argument("--debug", help="是否开启Debug模式" )
    parser.add_argument(
        "--config", type=str, default="config.yaml", help="YAML配置文件"
    )
    args = parser.parse_args()
    debug = False
    if args.debug:
        debug = True
    app = create_app(args.config)
    app.run(host=args.host, port=args.port, debug=debug)
    logger.info("Started flask app")
