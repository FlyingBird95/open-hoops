from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import database
from app.jsonapi import document

from .queries import fetch_player
from .router import router
from .serialize import serialize_player


@router.get("/{uid}")
def get_player(uid: str, db: Session = Depends(database.use_session)):
    player = fetch_player(db, uid)
    return document(data=serialize_player(player))
