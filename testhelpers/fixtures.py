"""Shared pytest fixtures — import into conftest and use directly."""

import pytest
from sqlalchemy.orm import Session

from .db import create_db_session, drop_db_session


@pytest.fixture(autouse=True)
def db() -> Session:
    session = create_db_session()
    yield session
    drop_db_session(session)
