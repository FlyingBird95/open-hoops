from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.jsonapi import document
from app.models import Player
from .serialize import serialize_player


def update_player(uid: str, body: dict, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.uid == uid).first()
    if not player:
        raise HTTPException(404, "Player not found")
    attrs = body["data"]["attributes"]
    for key, value in attrs.items():
        if hasattr(player, key) and key not in ("uid", "id", "team_id"):
            setattr(player, key, value)
    db.commit()
    db.refresh(player)
    return document(data=serialize_player(player))
