from fastapi import Depends
from sqlalchemy.orm import Session

from app.jsonapi import document
from open_hoops.core.database import get_db

from .queries import fetch_game
from .router import router
from .serialize import serialize_game


@router.get("/{uid}")
def get_game(uid: str, db: Session = Depends(get_db)):
    game = fetch_game(db, uid)
    return document(data=serialize_game(game))
