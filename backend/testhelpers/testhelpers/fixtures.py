"""Shared pytest fixtures — import into conftest and use directly."""

import pytest
from open_hoops.core.database import Base

from .db import ScopedSession, database


@pytest.fixture(autouse=True)
def db():
    Base.metadata.create_all(database.engine)
    session = ScopedSession()
    yield session
    ScopedSession.remove()
    Base.metadata.drop_all(database.engine)
