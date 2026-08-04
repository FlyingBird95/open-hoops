from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.jsonapi import document
from app.models import Team
from .serialize import serialize_team


def update_team(uid: str, body: dict, db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.uid == uid).first()
    if not team:
        raise HTTPException(404, "Team not found")
    attrs = body["data"]["attributes"]
    for key, value in attrs.items():
        if hasattr(team, key):
            setattr(team, key, value)
    db.commit()
    db.refresh(team)
    return document(data=serialize_team(team))
