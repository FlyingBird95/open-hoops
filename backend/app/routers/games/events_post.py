from fastapi import Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db, get_or_404
from app.jsonapi import document
from open_hoops.service.event.models import EventSource, GameEvent
from open_hoops.service.game.models import Game
from open_hoops.service.player.models import Player
from open_hoops.service.team.models import Team

from .serialize import serialize_event

EVENT_TYPES = {
    "shot",
    "make",
    "miss",
    "pass",
    "rebound",
    "turnover",
    "steal",
    "block",
    "foul",
    "assist",
    "substitution",
    "possession_change",
}


class EventCreateAttributes(BaseModel):
    type: str
    timestamp_sec: float
    frame: int
    team_uid: str | None = None
    player_uid: str | None = None
    player2_uid: str | None = None


class EventCreateData(BaseModel):
    type: str = "game_events"
    attributes: EventCreateAttributes


class EventCreateRequest(BaseModel):
    data: EventCreateData


def create_event(uid: str, body: EventCreateRequest, db: Session = Depends(get_db)):
    game = get_or_404(db, Game, uid)

    attrs = body.data.attributes
    if attrs.type not in EVENT_TYPES:
        raise HTTPException(422, f"Invalid event type: {attrs.type}")

    team_id = None
    if attrs.team_uid:
        team = db.query(Team).filter(Team.uid == attrs.team_uid).first()
        if not team:
            raise HTTPException(422, "Team not found")
        team_id = team.id

    player_id = None
    if attrs.player_uid:
        player = db.query(Player).filter(Player.uid == attrs.player_uid).first()
        if not player:
            raise HTTPException(422, "Player not found")
        player_id = player.id

    player2_id = None
    if attrs.player2_uid:
        player2 = db.query(Player).filter(Player.uid == attrs.player2_uid).first()
        if not player2:
            raise HTTPException(422, "Player2 not found")
        player2_id = player2.id

    event = GameEvent(
        game_id=game.id,
        type=attrs.type,
        frame=attrs.frame,
        timestamp_sec=attrs.timestamp_sec,
        team_id=team_id,
        player_id=player_id,
        player2_id=player2_id,
        source=EventSource.manual,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    return document(data=serialize_event(event))
