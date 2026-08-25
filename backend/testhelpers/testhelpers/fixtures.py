"""Shared pytest fixtures — import into conftest and use directly."""

import pytest
from open_hoops.core.database import Base

from .db import database
from .factories import ModelFactory


@pytest.fixture(autouse=True)
def db():
    Base.metadata.create_all(database.engine)
    session = database.session_factory()
    ModelFactory._meta.sqlalchemy_session = session
    yield session
    session.close()
    Base.metadata.drop_all(database.engine)
