from fastapi import Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db, get_or_404
from open_hoops.service.event.models import GameEvent
from open_hoops.service.game.models import Game


def delete_event(uid: str, event_id: int, db: Session = Depends(get_db)):
    game = get_or_404(db, Game, uid)

    event = (
        db.query(GameEvent).filter(GameEvent.id == event_id, GameEvent.game_id == game.id).first()
    )
    if not event:
        raise HTTPException(404, "Event not found")

    db.delete(event)
    db.commit()

    return Response(status_code=204)
