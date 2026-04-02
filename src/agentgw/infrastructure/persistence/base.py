from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def initialize_schema() -> None:
    from agentgw.infrastructure.persistence.models import DeliveryModel, SyncCursorModel  # noqa: F401

    Base.metadata.create_all(bind=engine)
