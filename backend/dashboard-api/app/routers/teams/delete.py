from fastapi import Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import database

from .queries import fetch_team
from .router import router


@router.delete("/{uid}")
def delete_team(uid: str, db: Session = Depends(database.use_session)):
    team = fetch_team(db, uid)
    db.delete(team)
    db.commit()
    return Response(status_code=204)
