"""Shared test database setup — import into each conftest.py."""

import os

from open_hoops.core.database import Database
from sqlalchemy.orm import scoped_session

TEST_DB_URL = os.environ.get(
    "OPEN_HOOPS_TEST_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/open_hoops_test",
)

database = Database(TEST_DB_URL)
ScopedSession = scoped_session(database.session_factory)
