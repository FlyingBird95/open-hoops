from fastapi import Depends
from sqlalchemy.orm import Session

from app.jsonapi import document
from open_hoops.core.database import get_db
from open_hoops.service.stats.models import GamePlayerStats, GameTeamStats

from .queries import fetch_game
from .router import router
from .serialize import serialize_player_stats, serialize_team_stats


@router.get("/{uid}/stats")
def get_game_stats(uid: str, db: Session = Depends(get_db)):
    game = fetch_game(db, uid)

    team_stats = db.query(GameTeamStats).filter(GameTeamStats.game_id == game.id).all()
    player_stats = db.query(GamePlayerStats).filter(GamePlayerStats.game_id == game.id).all()

    return document(
        data={
            "team_stats": [serialize_team_stats(ts) for ts in team_stats],
            "player_stats": [serialize_player_stats(ps) for ps in player_stats],
        },
    )
