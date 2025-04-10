import logging
from flask_socketio import Namespace, send, emit

logger = logging.getLogger(__name__)


class ControllerNamespace(Namespace):
    def __init__(self, namespace=None, app=None):
        super().__init__(namespace)
        self.app = app

    def on_connect(self):
        logger.info("Client connected")
        emit("my response", {"data": "Connected"})

    def on_disconnect(self, reason):
        logger.info(f"Client disconnected, reason: {reason}")

    def on_message(self, message):
        logger.info(f"Received message: {message}")
        send(f"Echo: {message}")


controller: ControllerNamespace


def register(socketio, app):
    """
    Register the socketio namespace with the Flask app.
    """
    controller = ControllerNamespace("/controller", app)
    socketio.on_namespace(controller)
    logger.info("SocketIO namespace registered")
