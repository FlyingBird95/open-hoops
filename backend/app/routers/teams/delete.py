from fastapi import Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db, get_or_404
from open_hoops.service.team.models import Team


def delete_team(uid: str, db: Session = Depends(get_db)):
    team = get_or_404(db, Team, uid)
    db.delete(team)
    db.commit()
    return Response(status_code=204)
