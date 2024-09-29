from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime, Index, UniqueConstraint
import sqlalchemy
import os
import logging

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass
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


class Test(Base):
    __tablename__ = "test"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = db.Column(String(50), nullable=False)


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
