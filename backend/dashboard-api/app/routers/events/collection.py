from fastapi import Depends, Query
from open_hoops.service.event.models import GameEvent
from open_hoops.service.game.models import Game
from sqlalchemy.orm import Session

from app.database import database
from app.jsonapi import document

from ..games import dependencies
from .router import router
from .serialize import serialize_event


@router.get("")
def list_events(
    game: Game = Depends(dependencies.get_game_by_query),
    type: str | None = Query(None),
    db: Session = Depends(database.use_session),
):
    q = db.query(GameEvent).filter(GameEvent.game == game)
    if type:
        q = q.filter(GameEvent.type == type)
    events = q.order_by(GameEvent.timestamp_sec).all()

    return document(
        data=[serialize_event(ev) for ev in events],
        meta={"count": len(events)},
    )
