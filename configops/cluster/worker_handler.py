from configops.cluster.messages import Message, MessageType
from configops.utils.constants import SystemType
from configops.config import get_database_cfg, get_node_cfg
import sqlalchemy, datetime
from configops.database.db import (
    db,
    ConfigOpsChangeLog,
    ConfigOpsChangeLogChanges,
    paginate,
)
from configops.database.utils import create_database_engine
from configops.api.utils import BaseResult
from configops.changelog import changelog_utils


class BaseMessageHandler:

    def handle(self, message: Message, namespace) -> BaseResult: ...


class QueryChangelogMessageHandler(BaseMessageHandler):

    def handle(self, message: Message, namespace) -> BaseResult:
        data = message.data
        system_id = data["system_id"]
        system_type = SystemType[data["system_type"]]

        if system_type == SystemType.DATABASE:
            db_config = get_database_cfg(namespace.app, system_id)
            items, total = self.__query_databae_change_log__(db_config, data)
            return BaseResult.ok(data=items, total=total)
        else:
            items, total = self.__query_change_log__(namespace.app, data)
            return BaseResult.ok(data=items, total=total)

    def __query_change_log__(self, app, data):
        system_id = data["system_id"]
        system_type = SystemType[data["system_type"]]
        page = int(data.get("page", 1))
        size = int(data.get("size", 20))
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        q = data.get("q")
        conditions = [
            ConfigOpsChangeLog.system_id == system_id,
            ConfigOpsChangeLog.system_type == system_type.name,
        ]

        if start_time:
            dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            conditions.append(ConfigOpsChangeLog.updated_at >= dt)
        if end_time:
            dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
            conditions.append(ConfigOpsChangeLog.updated_at <= dt)

        if q:
            conditions.append(
                sqlalchemy.or_(
                    ConfigOpsChangeLog.change_set_id.like(f"%{q}%"),
                    ConfigOpsChangeLog.author.like(f"%{q}%"),
                    ConfigOpsChangeLog.comment.like(f"%{q}%"),
                    ConfigOpsChangeLog.filename.like(f"%{q}%"),
                )
            )

        with app.app_context():
            stmt = (
                sqlalchemy.select(
                    ConfigOpsChangeLog.change_set_id,
                    ConfigOpsChangeLog.system_id,
                    ConfigOpsChangeLog.system_type,
                    ConfigOpsChangeLog.exectype,
                    ConfigOpsChangeLog.checksum,
                    ConfigOpsChangeLog.author,
                    ConfigOpsChangeLog.filename,
                    ConfigOpsChangeLog.comment,
                    ConfigOpsChangeLog.updated_at.label("execute_date"),
                )
                .where(*conditions)
                .order_by(ConfigOpsChangeLog.updated_at.desc())
            )
            items, total = paginate(stmt, page, size)
            final_items = [
                {
                    "change_set_id": item.change_set_id,
                    "system_id": item.system_id,
                    "system_type": item.system_type,
                    "exectype": item.exectype,
                    "checksum": item.checksum,
                    "author": item.author,
                    "filename": item.filename,
                    "comment": item.comment,
                    "execute_date": item.execute_date.strftime("%Y-%m-%d %H:%M:%S"),
                }
                for item in items
            ]
            return final_items, total

    def __query_databae_change_log__(self, db_config, data):
        if db_config is None:
            return [], 0
        system_id = data["system_id"]
        page = int(data.get("page", 1))
        size = int(data.get("size", 20))
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        q = data.get("q")
        engine = create_database_engine(db_config)
        metadata = sqlalchemy.MetaData()
        changelog = sqlalchemy.Table(
            "DATABASECHANGELOG", metadata, autoload_with=engine
        )

        conditions = []
        if start_time:
            dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            conditions.append(changelog.c.DATEEXECUTED >= dt)
        if end_time:
            dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
            conditions.append(changelog.c.DATEEXECUTED <= dt)
        if q:
            conditions.append(
                sqlalchemy.or_(
                    changelog.c.ID.like(f"%{q}%"),
                    changelog.c.AUTHOR.like(f"%{q}%"),
                    changelog.c.COMMENTS.like(f"%{q}%"),
                    changelog.c.FILENAME.like(f"%{q}%"),
                )
            )
        stmt = (
            sqlalchemy.select(
                changelog.c.ID.label("change_set_id"),
                changelog.c.EXECTYPE.label("exectype"),
                changelog.c.MD5SUM.label("checksum"),
                changelog.c.AUTHOR.label("author"),
                changelog.c.FILENAME.label("filename"),
                changelog.c.COMMENTS.label("comment"),
                changelog.c.DATEEXECUTED.label("execute_date"),
            )
            .where(*conditions)
            .order_by(changelog.c.DATEEXECUTED.desc())
        )

        with engine.connect() as conn:
            total_stmt = sqlalchemy.select(sqlalchemy.func.count()).select_from(
                stmt.subquery()
            )
            total = conn.execute(total_stmt).scalar()
            items = conn.execute(stmt.offset((page - 1) * size).limit(size)).all()
            final_items = [
                {
                    "change_set_id": item.change_set_id,
                    "system_id": system_id,
                    "system_type": SystemType.DATABASE.name,
                    "exectype": item.exectype,
                    "checksum": item.checksum,
                    "author": item.author,
                    "filename": item.filename,
                    "execute_date": item.execute_date.strftime("%Y-%m-%d %H:%M:%S"),
                }
                for item in items
            ]
            return final_items, total


class DeleteChangelogMessageHandler(BaseMessageHandler):
    def handle(self, message: Message, namespace) -> BaseResult:
        data = message.data
        system_id = data["system_id"]
        system_type = SystemType[data["system_type"]]
        change_set_ids = data["change_set_ids"]
        app = namespace.app
        if system_type == SystemType.DATABASE:
            db_config = get_database_cfg(app, system_id)
            engine = create_database_engine(db_config)
            metadata = sqlalchemy.MetaData()
            changelog = sqlalchemy.Table(
                "DATABASECHANGELOG", metadata, autoload_with=engine
            )
            stmt = sqlalchemy.delete(changelog).where(
                changelog.c.ID.in_(change_set_ids)
            )
            with engine.connect() as conn:
                conn.execute(stmt)
                conn.commit()
        else:
            with app.app_context():
                stmt = sqlalchemy.delete(ConfigOpsChangeLog).where(
                    ConfigOpsChangeLog.system_id == system_id,
                    ConfigOpsChangeLog.system_type == system_type.name,
                    ConfigOpsChangeLog.change_set_id.in_(change_set_ids),
                )
                db.session.execute(stmt)
                db.session.commit()
        return BaseResult.ok()


class QueryChangesetMessageHandler(BaseMessageHandler):
    def handle(self, message: Message, namespace) -> BaseResult:
        data = message.data
        change_set_id = data["change_set_id"]
        system_id = data["system_id"]
        system_type = SystemType[data["system_type"]]

        app = namespace.app
        with app.app_context():
            log_changes = (
                db.session.query(ConfigOpsChangeLogChanges)
                .filter(
                    ConfigOpsChangeLogChanges.change_set_id == change_set_id,
                    ConfigOpsChangeLogChanges.system_id == system_id,
                    ConfigOpsChangeLogChanges.system_type == system_type.name,
                )
                .first()
            )
            if log_changes is None:
                return BaseResult.ok()

            _secret = get_node_cfg(app)["secret"]
            changes = changelog_utils.unpack_encrypt_changes(
                log_changes.changes, _secret
            )
            return BaseResult.ok(data=changes)


# =====================================================================================================================================

MESSAGE_HANDLER_MAP = {
    MessageType.QUERY_CHANGE_LOG.name: QueryChangelogMessageHandler(),
    MessageType.DELETE_CHANGE_LOG.name: DeleteChangelogMessageHandler(),
    MessageType.QUERY_CHANGE_SET.name: QueryChangesetMessageHandler(),
}
