from fastapi import Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db, get_or_404
from app.jsonapi import document
from open_hoops.service.game.models import Game

from .serialize import serialize_game_file


def list_game_files(uid: str, db: Session = Depends(get_db)):
    game = get_or_404(db, Game, uid)

    return JSONResponse(
        content=document(
            data=[serialize_game_file(f) for f in game.files],
            meta={"count": len(game.files)},
        )
    )
