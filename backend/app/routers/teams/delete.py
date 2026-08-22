from fastapi import Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from open_hoops.core.database import get_db

from .queries import fetch_team
from .router import router


@router.delete("/{uid}")
def delete_team(uid: str, db: Session = Depends(get_db)):
    team = fetch_team(db, uid)
    db.delete(team)
    db.commit()
    return Response(status_code=204)
