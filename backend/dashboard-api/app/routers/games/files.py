from fastapi import Depends
from fastapi.responses import JSONResponse
from open_hoops.service.game.models import Game

from app.jsonapi import document

from . import dependencies
from .router import router
from .serialize import serialize_game_file


@router.get("/{uid}/files")
def list_game_files(game: Game = Depends(dependencies.get_game_by_uid)):
    return JSONResponse(
        content=document(
            data=[serialize_game_file(f) for f in game.files],
            meta={"count": len(game.files)},
        )
    )
