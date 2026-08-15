from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.jsonapi import document
from app.models import Team

from .serialize import serialize_team


def get_team(uid: str, db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.uid == uid).first()
    if not team:
        raise HTTPException(404, "Team not found")
    return document(data=serialize_team(team))
