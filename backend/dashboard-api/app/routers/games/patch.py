from fastapi import Depends
from open_hoops.service.game.models import Game
from sqlalchemy.orm import Session

from app.database import database
from app.jsonapi import document

from . import dependencies
from .router import router
from .serialize import serialize_game

ALLOWED_ATTRS = {"is_archived"}


@router.patch("/{uid}")
def update_game(
    body: dict,
    game: Game = Depends(dependencies.get_game_by_uid),
    db: Session = Depends(database.use_session),
):
    attrs = body.get("data", {}).get("attributes", {})
    for key, value in attrs.items():
        if key in ALLOWED_ATTRS:
            setattr(game, key, value)
    db.commit()
    db.refresh(game)
    return document(data=serialize_game(game))
