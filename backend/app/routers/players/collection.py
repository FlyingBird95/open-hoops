from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.database import database
from app.jsonapi import document
from open_hoops.service.player.models import Player

from .queries import fetch_team
from .router import router
from .serialize import serialize_player


@router.get("")
def list_players(team: str = Query(...), db: Session = Depends(database.use_session)):
    team_obj = fetch_team(db, team)
    players = db.query(Player).filter(Player.team_id == team_obj.id).all()
    return document(
        data=[serialize_player(p) for p in players],
        meta={"count": len(players)},
    )
