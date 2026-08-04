from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from typing import Generator

_engine = None
_SessionLocal = None


class Base(DeclarativeBase):
    pass


def get_engine(database_url: str | None = None):
    global _engine
    if database_url:
        _engine = create_engine(database_url)
    if _engine is None:
        raise RuntimeError("Database engine not initialized. Call get_engine(url) first.")
    return _engine


def get_session_factory(database_url: str | None = None) -> sessionmaker:
    global _SessionLocal
    if database_url or _SessionLocal is None:
        engine = get_engine(database_url)
        _SessionLocal = sessionmaker(bind=engine)
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    if _SessionLocal is None:
        raise RuntimeError("Database not initialized. Call get_session_factory(url) first.")
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
