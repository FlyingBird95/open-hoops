from fastapi import Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.jsonapi import document
from app.models import Game
from .serialize import serialize_game_file


def list_game_files(uid: str, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.uid == uid).first()
    if not game:
        raise HTTPException(404, "Game not found")

    return JSONResponse(
        content=document(
            data=[serialize_game_file(f) for f in game.files],
            meta={"count": len(game.files)},
        )
    )
