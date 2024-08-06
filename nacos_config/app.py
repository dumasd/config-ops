from flask import Flask
from .api.hello import bp as hello_bp
from .api.nacos import bp as nacos_bp
from .config import Config

def create_app() -> Flask:
    app = Flask(__name__)  
    app.register_blueprint(hello_bp)
    app.register_blueprint(nacos_bp)
    app.config.from_object(Config)
    return app