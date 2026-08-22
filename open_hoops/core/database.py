from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


class Database:
    def __init__(self, url: str):
        self.engine: Engine = create_engine(url)
        self.session_factory: sessionmaker[Session] = sessionmaker(bind=self.engine)

    def use_session(self) -> Generator[Session, None, None]:
        session = self.session_factory()
        try:
            yield session
        finally:
            session.close()

    @contextmanager
    def use_scoped_session(self) -> Generator[Session, None, None]:
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
