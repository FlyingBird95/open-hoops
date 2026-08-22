from fastapi import HTTPException
from sqlalchemy.orm import Session

from open_hoops.service.team.models import Team


def fetch_team(db: Session, uid: str) -> Team:
    team = db.query(Team).filter(Team.uid == uid).first()
    if not team:
        raise HTTPException(404, "Team not found")
    return team
