from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db, get_or_404
from app.jsonapi import document
from open_hoops.service.event.models import GameEvent

from .router import router
from .serialize import serialize_event


@router.get("/{uid}")
def get_event(uid: str, db: Session = Depends(get_db)):
    event = get_or_404(db, GameEvent, uid, label="Event")
    return document(data=serialize_event(event))
