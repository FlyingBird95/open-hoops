from fastapi import Depends
from fastapi.responses import Response
from open_hoops.service.team.models import Team
from sqlalchemy.orm import Session

from app.database import database

from . import dependencies
from .router import router


@router.delete("/{uid}")
def delete_team(
    team: Team = Depends(dependencies.get_team_by_uid),
    db: Session = Depends(database.use_session),
):
    db.delete(team)
    db.commit()
    return Response(status_code=204)
