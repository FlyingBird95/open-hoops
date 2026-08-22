from fastapi import Depends
from sqlalchemy.orm import Session

from app.jsonapi import document
from open_hoops.core.database import get_db

from .queries import fetch_team
from .router import router
from .serialize import serialize_team


@router.get("/{uid}")
def get_team(uid: str, db: Session = Depends(get_db)):
    team = fetch_team(db, uid)
    return document(data=serialize_team(team))
