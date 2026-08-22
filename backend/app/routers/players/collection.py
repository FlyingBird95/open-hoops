from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.jsonapi import document
from open_hoops.core.database import get_db
from open_hoops.service.player.models import Player

from .queries import fetch_team
from .router import router
from .serialize import serialize_player


@router.get("")
def list_players(team: str = Query(...), db: Session = Depends(get_db)):
    team_obj = fetch_team(db, team)
    players = db.query(Player).filter(Player.team_id == team_obj.id).all()
    return document(
        data=[serialize_player(p) for p in players],
        meta={"count": len(players)},
    )
