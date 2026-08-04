from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Player, Team
from app.schemas.players import PlayerCreate, PlayerUpdate, PlayerResponse

router = APIRouter(prefix="/api/players", tags=["players"])


def _player_response(player: Player) -> dict:
    return {
        "uid": player.uid,
        "team_uid": player.team.uid,
        "jersey_number": player.jersey_number,
        "name": player.name,
    }


@router.get("", response_model=list[PlayerResponse])
def list_players(team: str = Query(...), db: Session = Depends(get_db)):
    team_obj = db.query(Team).filter(Team.uid == team).first()
    if not team_obj:
        raise HTTPException(404, "Team not found")
    players = db.query(Player).filter(Player.team_id == team_obj.id).all()
    return [_player_response(p) for p in players]


@router.post("", response_model=PlayerResponse, status_code=201)
def create_player(data: PlayerCreate, db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.uid == data.team_uid).first()
    if not team:
        raise HTTPException(404, "Team not found")
    player = Player(team_id=team.id, jersey_number=data.jersey_number, name=data.name)
    db.add(player)
    db.commit()
    db.refresh(player)
    return _player_response(player)


@router.put("/{uid}", response_model=PlayerResponse)
def update_player(uid: str, data: PlayerUpdate, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.uid == uid).first()
    if not player:
        raise HTTPException(404, "Player not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(player, key, value)
    db.commit()
    db.refresh(player)
    return _player_response(player)


@router.delete("/{uid}", status_code=204)
def delete_player(uid: str, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.uid == uid).first()
    if not player:
        raise HTTPException(404, "Player not found")
    db.delete(player)
    db.commit()
