from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.jsonapi import document
from open_hoops.core.database import get_db
from open_hoops.service.event.models import GameEvent
from open_hoops.service.game.models import Game

from .router import router
from .serialize import serialize_event


@router.get("")
def list_events(
    game: str = Query(...),
    type: str | None = Query(None),
    db: Session = Depends(get_db),
):
    game_obj = db.query(Game).filter(Game.uid == game).first()
    if not game_obj:
        raise HTTPException(404, "Game not found")

    q = db.query(GameEvent).filter(GameEvent.game_id == game_obj.id)
    if type:
        q = q.filter(GameEvent.type == type)
    events = q.order_by(GameEvent.timestamp_sec).all()

    return document(
        data=[serialize_event(ev) for ev in events],
        meta={"count": len(events)},
    )
