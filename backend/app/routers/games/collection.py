from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.jsonapi import document
from open_hoops.core.database import get_db
from open_hoops.service.game.models import Game

from .router import router
from .serialize import serialize_game


@router.get("")
def list_games(archived: bool = Query(False), db: Session = Depends(get_db)):
    query = db.query(Game).filter(Game.is_archived == archived).order_by(Game.date.desc())
    games = query.all()
    return document(
        data=[serialize_game(g) for g in games],
        meta={"count": len(games)},
    )
