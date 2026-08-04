from fastapi import Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.jsonapi import document
from app.models import Player, Team
from .serialize import serialize_player


def create_player(body: dict, db: Session = Depends(get_db)):
    attrs = body["data"]["attributes"]
    rels = body["data"].get("relationships", {})
    team_uid = rels.get("team", {}).get("data", {}).get("uid")
    if not team_uid:
        raise HTTPException(422, "Missing relationship: team")
    team = db.query(Team).filter(Team.uid == team_uid).first()
    if not team:
        raise HTTPException(404, "Team not found")
    player = Player(
        team_id=team.id,
        jersey_number=attrs["jersey_number"],
        name=attrs.get("name"),
    )
    db.add(player)
    db.commit()
    db.refresh(player)
    return JSONResponse(content=document(data=serialize_player(player)), status_code=201)
