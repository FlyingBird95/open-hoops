from fastapi import Depends
from open_hoops.service.team.models import Team
from sqlalchemy.orm import Session

from app import exceptions
from app.database import database


def get_team_by_uid(uid: str, db: Session = Depends(database.use_session)) -> Team:
    team = db.query(Team).filter(Team.uid == uid).first()
    if not team:
        raise exceptions.NotFound("Team not found")
    return team
