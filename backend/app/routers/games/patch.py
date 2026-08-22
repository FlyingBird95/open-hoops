from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import database
from app.jsonapi import document

from .queries import fetch_game
from .router import router
from .serialize import serialize_game

ALLOWED_ATTRS = {"is_archived"}


@router.patch("/{uid}")
def update_game(uid: str, body: dict, db: Session = Depends(database.use_session)):
    game = fetch_game(db, uid)
    attrs = body.get("data", {}).get("attributes", {})
    for key, value in attrs.items():
        if key in ALLOWED_ATTRS:
            setattr(game, key, value)
    db.commit()
    db.refresh(game)
    return document(data=serialize_game(game))
