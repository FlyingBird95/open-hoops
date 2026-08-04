from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.jsonapi import document
from app.models import Game
from .serialize import serialize_game


def list_games(db: Session = Depends(get_db)):
    games = db.query(Game).order_by(Game.date.desc()).all()
    return document(
        data=[serialize_game(g) for g in games],
        meta={"count": len(games)},
    )
