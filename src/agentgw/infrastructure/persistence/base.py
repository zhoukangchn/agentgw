from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


_db_path = Path(__file__).resolve().parents[4] / ".agentgw.sqlite3"
engine = create_engine(f"sqlite+pysqlite:///{_db_path}", future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def initialize_schema() -> None:
    from agentgw.infrastructure.persistence.models import DeliveryModel, MessageModel, SyncCursorModel  # noqa: F401

    Base.metadata.create_all(bind=engine)
