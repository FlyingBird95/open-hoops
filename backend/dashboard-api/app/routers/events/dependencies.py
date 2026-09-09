from fastapi import Depends
from open_hoops.service.event.models import GameEvent
from sqlalchemy.orm import Session

from app import exceptions
from app.database import database


def get_event_by_uid(uid: str, db: Session = Depends(database.use_session)) -> GameEvent:
    event = db.query(GameEvent).filter(GameEvent.uid == uid).first()
    if not event:
        raise exceptions.NotFound("Event not found")
    return event
