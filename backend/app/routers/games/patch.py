from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.jsonapi import document
from app.models import Game
from .serialize import serialize_game

ALLOWED_ATTRS = {"is_archived"}


def update_game(uid: str, body: dict, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.uid == uid).first()
    if not game:
        raise HTTPException(404, "Game not found")
    attrs = body.get("data", {}).get("attributes", {})
    for key, value in attrs.items():
        if key in ALLOWED_ATTRS and hasattr(game, key):
            setattr(game, key, value)
    db.commit()
    db.refresh(game)
    return document(data=serialize_game(game))
