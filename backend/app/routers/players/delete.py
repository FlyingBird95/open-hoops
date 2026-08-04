from fastapi import Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Player


def delete_player(uid: str, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.uid == uid).first()
    if not player:
        raise HTTPException(404, "Player not found")
    db.delete(player)
    db.commit()
    return Response(status_code=204)
