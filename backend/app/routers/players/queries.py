from fastapi import HTTPException
from sqlalchemy.orm import Session

from open_hoops.service.player.models import Player
from open_hoops.service.team.models import Team


def fetch_player(db: Session, uid: str) -> Player:
    player = db.query(Player).filter(Player.uid == uid).first()
    if not player:
        raise HTTPException(404, "Player not found")
    return player


def fetch_team(db: Session, uid: str) -> Team:
    team = db.query(Team).filter(Team.uid == uid).first()
    if not team:
        raise HTTPException(404, "Team not found")
    return team
