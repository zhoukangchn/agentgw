from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


_db_path = Path(__file__).resolve().parents[4] / "agentgw.db"
engine = create_engine(f"sqlite+pysqlite:///{_db_path}", future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def configure_database(database_url: str) -> None:
    global engine
    engine.dispose()
    engine = create_engine(database_url, future=True)
    SessionLocal.configure(bind=engine)


def initialize_schema() -> None:
    from agentgw.infrastructure.persistence.models import AgentEndpointModel, ChannelModel, ConversationModel, MessageModel  # noqa: F401

    Base.metadata.create_all(bind=engine)
