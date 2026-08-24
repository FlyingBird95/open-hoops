from fastapi import HTTPException
from open_hoops.service.event.models import GameEvent
from sqlalchemy.orm import Session


def fetch_event(db: Session, uid: str) -> GameEvent:
    event = db.query(GameEvent).filter(GameEvent.uid == uid).first()
    if not event:
        raise HTTPException(404, "Event not found")
    return event
