from fastapi import Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.jsonapi import document
from app.models import Game, GameTeamStats, GamePlayerStats, GameEvent
from .serialize import serialize_team_stats, serialize_player_stats, serialize_event


def get_game_stats(uid: str, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.uid == uid).first()
    if not game:
        raise HTTPException(404, "Game not found")

    team_stats = db.query(GameTeamStats).filter(GameTeamStats.game_id == game.id).all()
    player_stats = db.query(GamePlayerStats).filter(GamePlayerStats.game_id == game.id).all()

    return document(
        data={
            "team_stats": [serialize_team_stats(ts) for ts in team_stats],
            "player_stats": [serialize_player_stats(ps) for ps in player_stats],
        },
    )


def get_game_events(
    uid: str,
    type: str | None = Query(None),
    db: Session = Depends(get_db),
):
    game = db.query(Game).filter(Game.uid == uid).first()
    if not game:
        raise HTTPException(404, "Game not found")

    q = db.query(GameEvent).filter(GameEvent.game_id == game.id)
    if type:
        q = q.filter(GameEvent.type == type)
    events = q.order_by(GameEvent.timestamp_sec).all()

    return document(
        data=[serialize_event(ev) for ev in events],
        meta={"count": len(events)},
    )
