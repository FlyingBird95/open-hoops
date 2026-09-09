from fastapi import Depends
from open_hoops.service.player.models import Player

from app.jsonapi import document

from . import dependencies
from .router import router
from .serialize import serialize_player


@router.get("/{uid}")
def get_player(player: Player = Depends(dependencies.get_player_by_uid)):
    return document(data=serialize_player(player))
