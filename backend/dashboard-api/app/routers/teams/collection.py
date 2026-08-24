from fastapi import Depends, Query
from open_hoops.service.team.models import Team
from sqlalchemy.orm import Session

from app.database import database
from app.jsonapi import document

from .router import router
from .serialize import serialize_team


@router.get("")
def list_teams(is_own: bool | None = Query(None), db: Session = Depends(database.use_session)):
    q = db.query(Team)
    if is_own is not None:
        q = q.filter(Team.is_own == is_own)
    teams = q.all()
    return document(
        data=[serialize_team(t) for t in teams],
        meta={"count": len(teams)},
    )
