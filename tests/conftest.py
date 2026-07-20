from __future__ import annotations

import pytest

from src.database import build_engine
from src.generator import create_schema


@pytest.fixture
def test_engine(tmp_path):
    engine = build_engine(f"sqlite:///{tmp_path / 'test.db'}")
    create_schema(engine)
    yield engine
    engine.dispose()
