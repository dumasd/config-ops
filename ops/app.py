from flask import Flask
import argparse
import logging
from .api.nacos import bp as nacos_bp
from .api.database import bp as database_bp
from .config import load_config
from .utils.logging_configurator import DefaultLoggingConfigurator

logger = logging.getLogger(__name__)

def create_app(config_file='config.yaml') -> Flask:
    app = Flask(__name__)
    app.register_blueprint(database_bp)
    app.register_blueprint(nacos_bp)
    config = load_config(config_file)
    app.config.update(config)
    loggingConfig = DefaultLoggingConfigurator()
    loggingConfig.configure_logging(config, debug_mode=False)
    return app

if __name__ == '__main__':
    logger.info("Starting flask app")
    parser = argparse.ArgumentParser(description='Run the config-ops application')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='服务Host')
    parser.add_argument('--port', type=int, default='5000', help='服务端口')
    parser.add_argument('--config', type=str, default='config.yaml', help='配置文件')
    args = parser.parse_known_args()
    logger.info(args)
    
    app = create_app(args['config'])
    app.run(host='0.0.0.0')
    logger.info("Started flask app")