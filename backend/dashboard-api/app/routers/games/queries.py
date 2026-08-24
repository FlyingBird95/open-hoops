from fastapi import HTTPException
from open_hoops.service.game.models import Game
from sqlalchemy.orm import Session


def fetch_game(db: Session, uid: str) -> Game:
    game = db.query(Game).filter(Game.uid == uid).first()
    if not game:
        raise HTTPException(404, "Game not found")
    return game
