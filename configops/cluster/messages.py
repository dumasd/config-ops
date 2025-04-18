from enum import Enum
import uuid


class MessageType(Enum):
    MANAGED_OBJECTS = "MANAGED_OBJECTS"  # worker->controller worker主动发送管理对象
    QUERY_CHANGE_LOG = "QUERY_CHANGE_LOG"  # 查询变更日志
    DELETE_CHANGE_LOG = "DELETE_CHANGE_LOG"  # 删除changelog
    EDIT_CHNAGE_LOG = "EDIT_CHANGE_LOG"  # 修改changelog


class Message:
    def __init__(
        self, type: MessageType = None, data=None, message=None, request_id: str = None
    ):
        if message:
            self.type = MessageType[message["type"]]
            self.data = message.get("data")
            self.request_id = message.get("request_id")
        else:
            self.type = type
            self.data = data
            self.request_id = request_id if request_id else str(uuid.uuid4())

    def to_dict(self):
        return {
            "type": self.type.name,
            "request_id": self.request_id,
            "data": self.data,
        }
