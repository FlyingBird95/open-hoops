from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import database
from app.jsonapi import document

from .queries import fetch_team
from .router import router
from .serialize import serialize_team


@router.get("/{uid}")
def get_team(uid: str, db: Session = Depends(database.use_session)):
    team = fetch_team(db, uid)
    return document(data=serialize_team(team))
