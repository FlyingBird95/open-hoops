from fastapi import Depends
from sqlalchemy.orm import Session

from app.jsonapi import document
from open_hoops.core.database import get_db

from .queries import fetch_event
from .router import router
from .serialize import serialize_event


@router.get("/{uid}")
def get_event(uid: str, db: Session = Depends(get_db)):
    event = fetch_event(db, uid)
    return document(data=serialize_event(event))
