from fastapi import Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Game, GameEvent


def delete_event(uid: str, event_id: int, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.uid == uid).first()
    if not game:
        raise HTTPException(404, "Game not found")

    event = (
        db.query(GameEvent).filter(GameEvent.id == event_id, GameEvent.game_id == game.id).first()
    )
    if not event:
        raise HTTPException(404, "Event not found")

    db.delete(event)
    db.commit()

    return Response(status_code=204)
