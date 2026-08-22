from fastapi import Depends, Response
from sqlalchemy.orm import Session

from app.database import get_db, get_or_404
from open_hoops.service.event.models import GameEvent

from .router import router


@router.delete("/{uid}")
def delete_event(uid: str, db: Session = Depends(get_db)):
    event = get_or_404(db, GameEvent, uid, label="Event")
    db.delete(event)
    db.commit()
    return Response(status_code=204)
