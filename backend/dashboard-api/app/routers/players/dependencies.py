from fastapi import Depends, Query
from open_hoops.service.player.models import Player
from open_hoops.service.team.models import Team
from sqlalchemy.orm import Session

from app import exceptions
from app.database import database


def get_player_by_uid(uid: str, db: Session = Depends(database.use_session)) -> Player:
    player = db.query(Player).filter(Player.uid == uid).first()
    if not player:
        raise exceptions.NotFound("Player not found")
    return player


def get_team_by_query(team: str = Query(...), db: Session = Depends(database.use_session)) -> Team:
    team_obj = db.query(Team).filter(Team.uid == team).first()
    if not team_obj:
        raise exceptions.NotFound("Team not found")
    return team_obj
