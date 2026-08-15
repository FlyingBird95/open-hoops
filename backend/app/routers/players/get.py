from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.jsonapi import document
from app.models import Player

from .serialize import serialize_player


def get_player(uid: str, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.uid == uid).first()
    if not player:
        raise HTTPException(404, "Player not found")
    return document(data=serialize_player(player))
