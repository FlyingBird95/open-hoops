from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db, get_or_404
from app.jsonapi import document
from open_hoops.service.player.models import Player
from open_hoops.service.team.models import Team

from .router import router
from .serialize import serialize_player


@router.get("")
def list_players(team: str = Query(...), db: Session = Depends(get_db)):
    team_obj = get_or_404(db, Team, team)
    players = db.query(Player).filter(Player.team_id == team_obj.id).all()
    return document(
        data=[serialize_player(p) for p in players],
        meta={"count": len(players)},
    )
