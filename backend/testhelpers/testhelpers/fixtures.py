"""Shared pytest fixtures — import into conftest and use directly."""

import pytest

from .db import Base, database


@pytest.fixture(autouse=True)
def db():
    Base.metadata.create_all(database.engine)
    yield
    Base.metadata.drop_all(database.engine)
