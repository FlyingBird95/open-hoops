from fastapi import Depends, Query
from open_hoops.service.game.models import Game
from sqlalchemy.orm import Session

from app.database import database
from app.jsonapi import document

from .router import router
from .serialize import serialize_game


@router.get("")
def list_games(archived: bool = Query(False), db: Session = Depends(database.use_session)):
    query = db.query(Game).filter(Game.is_archived == archived).order_by(Game.date.desc())
    games = query.all()
    return document(
        data=[serialize_game(g) for g in games],
        meta={"count": len(games)},
    )
