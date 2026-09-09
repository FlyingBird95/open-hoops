from fastapi import Depends
from open_hoops.service.player.models import Player
from open_hoops.service.team.models import Team
from sqlalchemy.orm import Session

from app.database import database
from app.jsonapi import document

from . import dependencies
from .router import router
from .serialize import serialize_player


@router.get("")
def list_players(
    team: Team = Depends(dependencies.get_team_by_query),
    db: Session = Depends(database.use_session),
):
    players = db.query(Player).filter(Player.team_id == team.id).all()
    return document(
        data=[serialize_player(p) for p in players],
        meta={"count": len(players)},
    )
