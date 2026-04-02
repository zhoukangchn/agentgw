from collections.abc import Iterator
from pathlib import Path

import pytest

from agentgw.infrastructure.persistence.base import engine, initialize_schema


@pytest.fixture(autouse=True)
def clean_persistence_state() -> Iterator[None]:
    db_path = Path(engine.url.database)
    engine.dispose()
    if db_path.exists():
        db_path.unlink()
    initialize_schema()
    yield
    engine.dispose()
