from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db, get_or_404
from app.jsonapi import document
from open_hoops.service.team.models import Team

from .router import router
from .serialize import serialize_team


@router.get("/{uid}")
def get_team(uid: str, db: Session = Depends(get_db)):
    team = get_or_404(db, Team, uid)
    return document(data=serialize_team(team))
