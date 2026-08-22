from fastapi import Depends
from sqlalchemy.orm import Session

from app.jsonapi import document
from open_hoops.core.database import get_db

from .queries import fetch_player
from .router import router
from .serialize import serialize_player


@router.get("/{uid}")
def get_player(uid: str, db: Session = Depends(get_db)):
    player = fetch_player(db, uid)
    return document(data=serialize_player(player))
