from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.jsonapi import document
from app.models import Player, Team
from .serialize import serialize_player


def list_players(team: str = Query(...), db: Session = Depends(get_db)):
    team_obj = db.query(Team).filter(Team.uid == team).first()
    if not team_obj:
        raise HTTPException(404, "Team not found")
    players = db.query(Player).filter(Player.team_id == team_obj.id).all()
    return document(
        data=[serialize_player(p) for p in players],
        meta={"count": len(players)},
    )
