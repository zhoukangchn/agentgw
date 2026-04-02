from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from agentgw.infrastructure.persistence.base import Base


@pytest.fixture
def sqlite_session_factory(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Iterator[sessionmaker]:
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'infra-test.sqlite3'}", future=True)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr("agentgw.infrastructure.persistence.repositories.delivery.initialize_schema", lambda: None)
    monkeypatch.setattr("agentgw.infrastructure.persistence.repositories.message.initialize_schema", lambda: None)
    monkeypatch.setattr("agentgw.infrastructure.persistence.repositories.sync.initialize_schema", lambda: None)
    yield sessionmaker(bind=engine, autoflush=False, autocommit=False)
    engine.dispose()
