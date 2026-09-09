from fastapi import Depends
from fastapi.responses import Response
from open_hoops.service.player.models import Player
from sqlalchemy.orm import Session

from app.database import database

from . import dependencies
from .router import router


@router.delete("/{uid}")
def delete_player(
    player: Player = Depends(dependencies.get_player_by_uid),
    db: Session = Depends(database.use_session),
):
    db.delete(player)
    db.commit()
    return Response(status_code=204)
