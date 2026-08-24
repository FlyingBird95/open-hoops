from datetime import datetime

from fastapi import Depends, Query
from open_hoops.service.game.models import GameLog
from sqlalchemy.orm import Session

from app.database import database
from app.jsonapi import document, resource_object

from .queries import fetch_game
from .router import router


@router.get("/{uid}/logs")
def list_game_logs(
    uid: str,
    after: str | None = Query(None),
    db: Session = Depends(database.use_session),
):
    game = fetch_game(db, uid)
    query = db.query(GameLog).filter(GameLog.game_id == game.id)
    if after:
        after_dt = datetime.fromisoformat(after)
        query = query.filter(GameLog.timestamp > after_dt)
    logs = query.order_by(GameLog.timestamp.asc()).all()
    data = [
        resource_object(
            type="game_logs",
            attributes={
                "timestamp": log.timestamp.isoformat(),
                "level": log.level.value,
                "message": log.message,
            },
        )
        for log in logs
    ]
    return document(data=data, meta={"count": len(data)})
