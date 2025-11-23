import logging
from flask import request
from flask_socketio import Namespace, emit, disconnect
from configops.utils.constants import CONTROLLER_NAMESPACE, FutureCallback
from configops.database.db import (
    db,
    Worker,
    ManagedObjects,
    GroupPermission,
)
from configops.cluster.messages import Message, MessageType
from configops.utils.exception import ConfigOpsException
from typing import Optional

logger = logging.getLogger(__name__)


class ClusterWorkerInfo:
    def __init__(self, id, sid, name):
        self.id = id
        self.sid = sid
        self.name = name


class ControllerNamespace(Namespace):
    def __init__(self, namespace=None, app=None):
        super().__init__(namespace)
        self.app = app
        self.worker_map = {}
        self.send_callback_map = {}

    def is_worker_online(self, worker_id) -> Optional[ClusterWorkerInfo]:
        for worker_info in self.worker_map.values():
            if worker_info.id == worker_id:
                return worker_info
        return None

    def send_message(self, worker_id, message: Message, callback: FutureCallback = None):
        worker_info = self.is_worker_online(worker_id)
        if worker_info:
            emit(
                "message",
                message.to_dict(),
                to=worker_info.sid,
                namespace=self.namespace,
                broadcast=False,
            )
            if callback:
                self.send_callback_map[message.request_id] = callback
        elif callback:
            callback.on_error(ConfigOpsException("Worker is offline"))

    def on_connect(self, auth):
        worker_name = auth["name"]
        worker_secret = auth["secret"]
        worker = db.session.query(Worker).filter(Worker.name == worker_name).first()
        if not worker:
            emit(
                "error",
                {"message": "Connection Failure: Not found worker in controller"},
                to=request.sid,
                namespace=self.namespace,
                broadcast=False,
            )
            disconnect()
        if worker_secret != worker.secret:
            emit(
                "error",
                {"message": "Connection Failure: Unauthorized"},
                to=request.sid,
                namespace=self.namespace,
                broadcast=False,
            )
            disconnect()
        worker_info = ClusterWorkerInfo(worker.id, request.sid, worker.name)
        self.worker_map[request.sid] = worker_info

    def on_disconnect(self, reason):
        logger.info(f"Client disconnected, reason: {reason}")
        disconnect()
        self.worker_map.pop(request.sid)

    def on_message(self, msg):
        logger.info(f"Received message: {msg}")
        message = Message(message=msg)
        handler = MESSAGE_HANDLER_MAP.get(message.type.name)
        if handler:
            handler.handle(request.sid, message, self)


class BaseMessageHandler:

    def handle(self, sid, message: Message, namespace: ControllerNamespace): ...


class ManagedObjectsMessageHandler(BaseMessageHandler):

    def handle_managed_objects(self, worker_info, items):
        add_objects = []
        remain_ids = []
        for item in items:
            managed_object = (
                db.session.query(ManagedObjects)
                .filter(
                    ManagedObjects.worker_id == worker_info.id,
                    ManagedObjects.system_id == item["id"],
                    ManagedObjects.system_type == item["system_type"],
                )
                .first()
            )
            if managed_object:
                managed_object.url = item["url"]
                remain_ids.append(managed_object.id)
            else:
                managed_object = ManagedObjects(
                    worker_id=worker_info.id,
                    system_id=item["id"],
                    system_type=item["system_type"],
                    url=item["url"],
                )
                add_objects.append(managed_object)

        delete_objects = (
            db.session.query(ManagedObjects)
            .filter(
                ManagedObjects.worker_id == worker_info.id,
                ManagedObjects.id.not_in(remain_ids),
            )
            .all()
        )

        if len(delete_objects) > 0:
            object_ids = [item.id for item in delete_objects]

            db.session.query(GroupPermission).filter(
                GroupPermission.source_id.in_(object_ids),
                GroupPermission.type == "OBJECT",
            ).delete()

            for item in delete_objects:
                db.session.delete(item)

        if len(add_objects) > 0:
            db.session.add_all(add_objects)

        db.session.commit()

    def handle(self, sid, message: Message, namespace: ControllerNamespace):
        logger.info("Handle managed objects")
        worker_info = namespace.worker_map[sid]
        self.handle_managed_objects(worker_info, message.data)


class WorkerInfoMessageHandler(ManagedObjectsMessageHandler):
    def handle(self, sid, message: Message, namespace: ControllerNamespace):
        logger.info("Handle worker info")
        worker_info = namespace.worker_map[sid]
        self.handle_managed_objects(worker_info, message.data["managed_objects"])
        worker = db.session.query(Worker).filter(Worker.id == worker_info.id).first()
        worker.version = message.data["version"]
        db.session.commit()


class CommonFuturedMessageHandler(BaseMessageHandler):
    
    def handle(self, sid, message: Message, namespace: ControllerNamespace):
        callable = namespace.send_callback_map.pop(message.request_id)
        if callable:
            callable.on_complete(message.data)

MESSAGE_HANDLER_MAP = {}


def register(socketio, app) -> ControllerNamespace:
    """
    Register the socketio namespace with the Flask app.
    """
    MESSAGE_HANDLER_MAP[MessageType.MANAGED_OBJECTS.name] = (
        ManagedObjectsMessageHandler()
    )
    MESSAGE_HANDLER_MAP[MessageType.WORKER_INFO.name] = WorkerInfoMessageHandler()
    MESSAGE_HANDLER_MAP[MessageType.QUERY_CHANGE_LOG.name] = (
        CommonFuturedMessageHandler()
    )
    MESSAGE_HANDLER_MAP[MessageType.DELETE_CHANGE_LOG.name] = (
        CommonFuturedMessageHandler()
    )
    MESSAGE_HANDLER_MAP[MessageType.EDIT_CHNAGE_LOG.name] = (
        CommonFuturedMessageHandler()
    )
    MESSAGE_HANDLER_MAP[MessageType.QUERY_CHANGE_SET.name] = (
        CommonFuturedMessageHandler()
    )
    MESSAGE_HANDLER_MAP[MessageType.QUERY_SECRET.name] = (
        CommonFuturedMessageHandler()
    )
    MESSAGE_HANDLER_MAP[MessageType.UPGRADE_WORKER.name] = CommonFuturedMessageHandler()

    controller = ControllerNamespace("/controller", app)
    socketio.on_namespace(controller)
    app.config[CONTROLLER_NAMESPACE] = controller
    logger.info("SocketIO namespace registered")
