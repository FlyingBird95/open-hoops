from fastapi import Depends
from open_hoops.service.game.models import Game

from app.jsonapi import document

from . import dependencies
from .router import router
from .serialize import serialize_game


@router.get("/{uid}")
def get_game(game: Game = Depends(dependencies.get_game_by_uid)):
    return document(data=serialize_game(game))
