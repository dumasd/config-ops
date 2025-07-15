from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import (
    String,
    BigInteger,
    Integer,
    DateTime,
    LargeBinary,
    UniqueConstraint,
    func,
    select,
)
import sqlalchemy
import os
import logging
import uuid

logger = logging.getLogger(__name__)

_BASE_SQL_DIR = "migrations/sql"


class Base(DeclarativeBase):
    created_at = mapped_column(
        DateTime,
        default=sqlalchemy.func.now(),
        nullable=False,
    )
    updated_at = mapped_column(
        DateTime,
        default=sqlalchemy.func.now(),
        onupdate=sqlalchemy.func.now(),
        nullable=False,
    )

    def to_dict(self):
        return {
            column.key: getattr(self, column.key) for column in self.__table__.columns
        }


db = SQLAlchemy(model_class=Base)


class ConfigOpsChangeLog(Base):
    __tablename__ = "CONFIGOPS_CHANGE_LOG"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    change_set_id = mapped_column(String(100), nullable=False, comment="变更集ID")
    system_id = mapped_column(String(32), nullable=False, comment="系统ID")
    system_type = mapped_column(String(30), nullable=False, comment="系统类型")
    exectype = mapped_column(String(30), nullable=False, comment="执行类型")
    checksum = mapped_column(String(128), nullable=True, comment="checksum")
    author = mapped_column(String(128), comment="作者")
    filename = mapped_column(String(1024))
    # contexts = mapped_column(String(1024), comment="执行上下文")
    comment = mapped_column(String(2048))
    __table_args__ = (
        UniqueConstraint(
            "change_set_id", "system_type", "system_id", name="uix_change"
        ),
    )


class ConfigOpsChangeLogChanges(Base):
    __tablename__ = "CONFIGOPS_CHANGE_LOG_CHANGES"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    change_set_id = mapped_column(String(100), nullable=False, comment="变更集ID")
    system_id = mapped_column(String(32), nullable=False, comment="系统ID")
    system_type = mapped_column(String(30), nullable=False, comment="系统类型")
    changes: Mapped[bytes] = mapped_column(
        LargeBinary(length=(2**32) - 1), comment="变更数据"
    )
    __table_args__ = (
        UniqueConstraint(
            "change_set_id", "system_type", "system_id", name="uix_change"
        ),
    )


class ConfigOpsProvisionSecret(Base):
    __tablename__ = "CONFIGOPS_PROVISION_SECRET"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    system_id = mapped_column(String(32), nullable=False, comment="系统ID")
    system_type = mapped_column(String(30), nullable=False, comment="系统类型")
    object = mapped_column(String(255), nullable=False, comment="密钥对象")
    username = mapped_column(String(255), nullable=False, comment="账号")
    password: Mapped[bytes] = mapped_column(LargeBinary, nullable=False, comment="密码")
    extra = mapped_column(String(2014), nullable=True, comment="Extra")


table_name_prefix = "configops_"


class MigrationHistory(Base):
    __tablename__ = f"{table_name_prefix}migration_history"
    fname = mapped_column(String(255), primary_key=True)


class Workspace(Base):
    __tablename__ = f"{table_name_prefix}workspace"
    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = mapped_column(String(50), nullable=False)
    description = mapped_column(String(255), nullable=True)


class Worker(Base):
    __tablename__ = f"{table_name_prefix}worker"
    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = mapped_column(String(36), nullable=False)
    name = mapped_column(String(50), nullable=False)
    secret = mapped_column(String(255), nullable=False)
    description = mapped_column(String(255), nullable=True)
    version = mapped_column(String(20), nullable=True)

    __table_args__ = (UniqueConstraint("name", name="uniq_name"),)


class ManagedObjects(Base):
    __tablename__ = f"{table_name_prefix}managed_objects"
    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    worker_id = mapped_column(String(36), nullable=False)
    system_id = mapped_column(String(128), nullable=False)
    system_type = mapped_column(String(30), nullable=False)
    url = mapped_column(String(512), nullable=False)
    __table_args__ = (
        UniqueConstraint(
            "worker_id", "system_type", "system_id", name="uniq_object_key"
        ),
    )


class User(Base):
    __tablename__ = f"{table_name_prefix}user"
    id = mapped_column(String(32), primary_key=True, nullable=False)
    name = mapped_column(String(255), primary_key=True, nullable=False)
    email = mapped_column(String(64), nullable=True)
    status = mapped_column(String(12), nullable=False, default="active")
    source = mapped_column(String(32), nullable=False)


class Group(Base):
    __tablename__ = f"{table_name_prefix}group"
    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = mapped_column(String(50), nullable=False)
    description = mapped_column(String(255), nullable=True)


class UserGroup(Base):
    __tablename__ = f"{table_name_prefix}user_group"
    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = mapped_column(String(36), nullable=False)
    group_id = mapped_column(String(36), nullable=False)
    __table_args__ = (
        UniqueConstraint("user_id", "group_id", name="uniq_user_id_group_id"),
    )


class GroupPermission(Base):
    __tablename__ = f"{table_name_prefix}group_permission"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    group_id = mapped_column(String(36), nullable=False)
    source_id = mapped_column(String(36), nullable=False)
    type = mapped_column(String(10), nullable=False)
    permission = mapped_column(String(128), nullable=False)


def paginate(stmt, page: int = 1, size: int = 10):
    total_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.session.execute(total_stmt).scalar()
    items = db.session.execute(stmt.offset((page - 1) * size).limit(size)).all()
    return items, total


def init(app, node_config):
    if app.config.get("SQLALCHEMY_DATABASE_URI") is None:
        db_uri = None
        cfg = app.config.get("config")
        if cfg is not None and cfg.get("database-uri") is not None:
            db_uri = cfg.get("database-uri")
        if db_uri is None:
            db_uri = os.getenv("SQLALCHEMY_DATABASE_URI")
        if db_uri is None:
            db_uri = "sqlite:///configops.db"
        app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
    db.init_app(app)
    with app.app_context():
        db.create_all()

        result = db.session.query(MigrationHistory).all()
        executed = {row.fname for row in result}
        sql_dir = _BASE_SQL_DIR + "/" + node_config["role"]
        if os.path.exists(sql_dir):
            for fname in sorted(os.listdir(sql_dir)):
                if fname.endswith(".sql") and fname not in executed:
                    path = os.path.join(sql_dir, fname)
                    with open(path, "r") as f:
                        sql_list = f.read().split(";")
                        for sql in sql_list:
                            if sql.strip():
                                db.session.execute(sqlalchemy.text(sql.strip()))
                        db.session.add(MigrationHistory(fname=fname))
                        db.session.commit()
