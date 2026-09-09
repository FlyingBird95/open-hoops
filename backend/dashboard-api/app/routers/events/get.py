from fastapi import Depends
from open_hoops.service.event.models import GameEvent

from app.jsonapi import document

from . import dependencies
from .router import router
from .serialize import serialize_event


@router.get("/{uid}")
def get_event(event: GameEvent = Depends(dependencies.get_event_by_uid)):
    return document(data=serialize_event(event))
