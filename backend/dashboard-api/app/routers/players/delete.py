from fastapi import Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import database

from .queries import fetch_player
from .router import router


@router.delete("/{uid}")
def delete_player(uid: str, db: Session = Depends(database.use_session)):
    player = fetch_player(db, uid)
    db.delete(player)
    db.commit()
    return Response(status_code=204)
