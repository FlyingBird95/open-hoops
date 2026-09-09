from fastapi import Depends
from open_hoops.service.team.models import Team

from app.jsonapi import document

from . import dependencies
from .router import router
from .serialize import serialize_team


@router.get("/{uid}")
def get_team(team: Team = Depends(dependencies.get_team_by_uid)):
    return document(data=serialize_team(team))
