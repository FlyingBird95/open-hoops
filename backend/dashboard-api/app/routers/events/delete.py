from http import HTTPStatus

from fastapi import Depends, Response
from open_hoops.service.event.models import GameEvent
from sqlalchemy.orm import Session

from app.database import database

from . import dependencies
from .router import router


@router.delete("/{uid}")
def delete_event(
    event: GameEvent = Depends(dependencies.get_event_by_uid),
    db: Session = Depends(database.use_session),
):
    db.delete(event)
    db.commit()
    return Response(status_code=HTTPStatus.NO_CONTENT)
