import logging
import socketio
import time
from configops.utils.exception import ConfigOpsException
from configops.utils.constants import (
    WORKER_NAMESPACE,
    SystemType,
)
import configops
from configops.config import get_config
from configops.cluster.messages import Message, MessageType
from configops.cluster.worker_handler import MESSAGE_HANDLER_MAP
from configops.config import get_node_cfg
from configops.api.utils import BaseResult
from urllib.parse import urlparse


logger = logging.getLogger(__name__)

sio = socketio.Client(
    reconnection=True,
    reconnection_delay_max=10,
    reconnection_delay=2,
    logger=True,
    engineio_logger=True,
)


class WorkerNamespace(socketio.ClientNamespace):
    def __init__(self, app, namespace=None):
        super().__init__(namespace)
        self.app = app

    def on_error(self, data):
        logger.error(f"Error: {data}")

    def on_connect(self):
        logger.info("Connected to the controller")
        managed_objects = []
        nacos_cfg_map = get_config(self.app, "nacos")
        if nacos_cfg_map and len(nacos_cfg_map) > 0:
            for key, item in nacos_cfg_map.items():
                managed_objects.append(
                    {
                        "id": key,
                        "system_type": SystemType.NACOS.name,
                        "url": item.get("url"),
                        "dialect": "",
                    }
                )
        database_cfg_map = get_config(self.app, "database")
        if database_cfg_map and len(database_cfg_map) > 0:
            for key, item in database_cfg_map.items():
                host = item.get("url")
                port = item.get("port", 3306)
                managed_objects.append(
                    {
                        "id": key,
                        "system_type": SystemType.DATABASE.name,
                        "url": f"{host}:{port}",
                        "dialect": item.get("dialect", "mysql"),
                    }
                )
        elasticsearch_cfg_map = get_config(self.app, "elasticsearch")
        if elasticsearch_cfg_map and len(elasticsearch_cfg_map) > 0:
            for key, item in elasticsearch_cfg_map.items():
                managed_objects.append(
                    {
                        "id": key,
                        "system_type": SystemType.ELASTICSEARCH.name,
                        "url": item.get("url"),
                        "dialect": "",
                    }
                )
        graphdb_cfg_map = get_config(self.app, "graphdb")
        if graphdb_cfg_map and len(graphdb_cfg_map) > 0:
            for key, item in graphdb_cfg_map.items():
                managed_objects.append(
                    {
                        "id": key,
                        "system_type": SystemType.GRAPHDB.name,
                        "url": f"{item.get("host")}:{item.get("port")}",
                        "dialect": "",
                    }
                )
        data = {"version": configops.__version__, "managed_objects": managed_objects}
        message = Message(type=MessageType.WORKER_INFO, data=data)
        self.send(message.to_dict())

    def on_disconnect(self):
        logger.info("❌ Disconnected from controller")
        # self.connect_with_retry()

    def on_connect_error(self, data):
        print("⚠️ Connection failed:", data)

    def on_reconnect(self):
        print("🔄 Reconnected")

    def on_message(self, msg):
        req = Message(message=msg)
        resp = None
        try:
            handler = MESSAGE_HANDLER_MAP.get(req.type.name)
            handle_result = BaseResult.ok()
            if handler:
                handle_result = handler.handle(req, self)
            else:
                pass
            resp = Message(
                type=req.type,
                data=handle_result.to_dict(),
                request_id=req.request_id,
            )
        except Exception as ex:
            # 返回异常
            logger.error(
                f"An error when executing [{req.type}] command. exception: {ex}",
                exc_info=True,
            )
            resp = Message(
                type=req.type,
                data=BaseResult.error(
                    f"An error when executing [{req.type}] command. exception: {ex}"
                ).to_dict(),
                request_id=req.request_id,
            )
        self.send(resp.to_dict())

    def connect_with_retry(self):
        node_config = get_node_cfg(self.app)
        controller_url = node_config.get("controller_url")
        if not controller_url:
            return
        name = node_config.get("name")
        if not name:
            raise ConfigOpsException("[config.node.name] is empty")
        secret = node_config.get("secret")

        if not secret:
            raise ConfigOpsException("[config.node.secret] is empty")

        controller_url_parsed = urlparse(controller_url)

        connection_url = (
            f"{controller_url_parsed.scheme}://{controller_url_parsed.hostname}"
        )
        if controller_url_parsed.port:
            connection_url += f":{controller_url_parsed.port}"

        socketio_path = controller_url_parsed.path
        if socketio_path and socketio_path.startswith("/"):
            socketio_path = socketio_path[1:]
        if not socketio_path:
            socketio_path = "socket.io"

        while not sio.connected:
            try:
                logger.info("Trying to connect")
                sio.connect(
                    url=connection_url,
                    auth={"name": name, "secret": secret},
                    namespaces=["/controller"],
                    socketio_path=socketio_path,
                )
            except Exception as e:
                logger.info(f"Connect fail. retry. {e}")
                time.sleep(5)


# =======================================================================================


def register(app):
    worker_namespace = WorkerNamespace(app, "/controller")
    sio.register_namespace(worker_namespace)
    app.config[WORKER_NAMESPACE] = worker_namespace
    worker_namespace.connect_with_retry()
