from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import database
from app.jsonapi import document

from .queries import fetch_game
from .router import router
from .serialize import serialize_game


@router.get("/{uid}")
def get_game(uid: str, db: Session = Depends(database.use_session)):
    game = fetch_game(db, uid)
    return document(data=serialize_game(game))
