from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db, get_or_404
from app.jsonapi import document
from open_hoops.service.game.models import Game

from .serialize import serialize_game


def get_game(uid: str, db: Session = Depends(get_db)):
    game = get_or_404(db, Game, uid)
    return document(data=serialize_game(game))
