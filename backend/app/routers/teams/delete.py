from fastapi import Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Team


def delete_team(uid: str, db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.uid == uid).first()
    if not team:
        raise HTTPException(404, "Team not found")
    db.delete(team)
    db.commit()
    return Response(status_code=204)
