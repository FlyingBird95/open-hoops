from fastapi import HTTPException
from sqlalchemy.orm import Session

from open_hoops.service.event.models import GameEvent


def fetch_event(db: Session, uid: str) -> GameEvent:
    event = db.query(GameEvent).filter(GameEvent.uid == uid).first()
    if not event:
        raise HTTPException(404, "Event not found")
    return event
