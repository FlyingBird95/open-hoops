from fastapi import Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.jsonapi import document
from app.models import Team
from .serialize import serialize_team


def create_team(body: dict, db: Session = Depends(get_db)):
    attrs = body["data"]["attributes"]
    team = Team(
        name=attrs["name"],
        is_own=attrs.get("is_own", False),
        home_color=attrs.get("home_color", "#000000"),
        away_color=attrs.get("away_color", "#ffffff"),
    )
    db.add(team)
    db.commit()
    db.refresh(team)
    return JSONResponse(content=document(data=serialize_team(team)), status_code=201)
