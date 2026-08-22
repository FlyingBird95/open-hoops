from fastapi import Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import database
from app.jsonapi import document

from .queries import fetch_player
from .router import router
from .serialize import serialize_player


class PlayerPatchAttributes(BaseModel):
    jersey_number: int | None = None
    name: str | None = None


class PlayerPatchData(BaseModel):
    type: str = "players"
    attributes: PlayerPatchAttributes


class PlayerPatchRequest(BaseModel):
    data: PlayerPatchData


@router.patch("/{uid}")
def update_player(uid: str, body: PlayerPatchRequest, db: Session = Depends(database.use_session)):
    player = fetch_player(db, uid)
    for key, value in body.data.attributes.model_dump(exclude_unset=True).items():
        setattr(player, key, value)
    db.commit()
    db.refresh(player)
    return document(data=serialize_player(player))
