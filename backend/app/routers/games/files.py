from fastapi import Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import database
from app.jsonapi import document

from .queries import fetch_game
from .router import router
from .serialize import serialize_game_file


@router.get("/{uid}/files")
def list_game_files(uid: str, db: Session = Depends(database.use_session)):
    game = fetch_game(db, uid)

    return JSONResponse(
        content=document(
            data=[serialize_game_file(f) for f in game.files],
            meta={"count": len(game.files)},
        )
    )
