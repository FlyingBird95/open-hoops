from fastapi import HTTPException
from open_hoops.service.team.models import Team
from sqlalchemy.orm import Session


def fetch_team(db: Session, uid: str) -> Team:
    team = db.query(Team).filter(Team.uid == uid).first()
    if not team:
        raise HTTPException(404, "Team not found")
    return team
