from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db, get_or_404
from app.jsonapi import document
from open_hoops.service.player.models import Player

from .serialize import serialize_player


def get_player(uid: str, db: Session = Depends(get_db)):
    player = get_or_404(db, Player, uid)
    return document(data=serialize_player(player))
