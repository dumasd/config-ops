from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime, Index, UniqueConstraint
import sqlalchemy
import os
import logging
import uuid

logger = logging.getLogger(__name__)


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
    comment = mapped_column(String(2048))

    __table_args__ = (
        UniqueConstraint(
            "change_set_id", "system_type", "system_id", name="uix_change"
        ),
    )


table_name_prefix = "configops_"


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


class ManagedObjects(Base):
    __tablename__ = f"{table_name_prefix}managed_objects"
    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    worker_id = mapped_column(String(36), nullable=False)
    key = mapped_column(String(128), nullable=False)
    system_type = mapped_column(String(30), nullable=False)
    url = mapped_column(String(512), nullable=False)


class User(Base):
    __tablename__ = f"{table_name_prefix}user"
    id = mapped_column(String(32), primary_key=True, nullable=False)
    email = mapped_column(String(64), nullable=True)
    status = mapped_column(String(12), nullable=False, default="active")
    source = mapped_column(String(32), nullable=False)


class Group(Base):
    __tablename__ = f"{table_name_prefix}group"
    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = mapped_column(String(50), nullable=False)
    description = mapped_column(String(255), nullable=True)
    type = mapped_column(String(10), nullable=False)
    scope_id = mapped_column(String(36), nullable=False)


class GroupPermission(Base):
    __tablename__ = f"{table_name_prefix}group_permission"
    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_id = mapped_column(String(36), nullable=False)
    permission_id = mapped_column(String(72), nullable=False)
    module_id = mapped_column(String(72), nullable=False)


class UserGroup(Base):
    __tablename__ = f"{table_name_prefix}user_group"
    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = mapped_column(String(36), nullable=False)
    group_id = mapped_column(String(36), nullable=False)
    source_id = mapped_column(String(36), nullable=False)


def init(app):
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
