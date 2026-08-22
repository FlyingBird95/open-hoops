from fastapi import Depends, Response
from sqlalchemy.orm import Session

from app.database import database

from .queries import fetch_event
from .router import router


@router.delete("/{uid}")
def delete_event(uid: str, db: Session = Depends(database.use_session)):
    event = fetch_event(db, uid)
    db.delete(event)
    db.commit()
    return Response(status_code=204)
