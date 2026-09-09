from fastapi import Depends, Query
from open_hoops.service.game.models import Game
from sqlalchemy.orm import Session

from app import exceptions
from app.database import database


def get_game_by_query(game: str = Query(...), db: Session = Depends(database.use_session)) -> Game:
    game_obj = db.query(Game).filter(Game.uid == game).first()
    if not game_obj:
        raise exceptions.BadRequest("Game not found")

    return game_obj


def get_game_by_uid(uid: str, db: Session = Depends(database.use_session)) -> Game:
    game_obj = db.query(Game).filter(Game.uid == uid).first()
    if not game_obj:
        raise exceptions.NotFound("Game not found")

    return game_obj
