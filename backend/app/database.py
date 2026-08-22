from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from open_hoops.core.database import get_engine, get_session_factory

get_engine(settings.database_url)
get_session_factory(settings.database_url)


def get_or_404(db: Session, model, uid: str, label: str | None = None):
    obj = db.query(model).filter(model.uid == uid).first()
    if not obj:
        name = label or model.__tablename__.rstrip("s").replace("_", " ").title()
        raise HTTPException(404, f"{name} not found")
    return obj
