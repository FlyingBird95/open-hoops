from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import database
from app.jsonapi import document

from .queries import fetch_event
from .router import router
from .serialize import serialize_event


@router.get("/{uid}")
def get_event(uid: str, db: Session = Depends(database.use_session)):
    event = fetch_event(db, uid)
    return document(data=serialize_event(event))
