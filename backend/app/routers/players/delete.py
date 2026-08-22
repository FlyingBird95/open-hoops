from fastapi import Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db, get_or_404
from open_hoops.service.player.models import Player

from .router import router


@router.delete("/{uid}")
def delete_player(uid: str, db: Session = Depends(get_db)):
    player = get_or_404(db, Player, uid)
    db.delete(player)
    db.commit()
    return Response(status_code=204)
