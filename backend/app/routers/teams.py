from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Team
from app.schemas.teams import TeamCreate, TeamUpdate, TeamResponse

router = APIRouter(prefix="/api/teams", tags=["teams"])


@router.get("", response_model=list[TeamResponse])
def list_teams(is_own: bool | None = Query(None), db: Session = Depends(get_db)):
    q = db.query(Team)
    if is_own is not None:
        q = q.filter(Team.is_own == is_own)
    return q.all()


@router.post("", response_model=TeamResponse, status_code=201)
def create_team(data: TeamCreate, db: Session = Depends(get_db)):
    team = Team(**data.model_dump())
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


@router.get("/{uid}", response_model=TeamResponse)
def get_team(uid: str, db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.uid == uid).first()
    if not team:
        raise HTTPException(404, "Team not found")
    return team


@router.put("/{uid}", response_model=TeamResponse)
def update_team(uid: str, data: TeamUpdate, db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.uid == uid).first()
    if not team:
        raise HTTPException(404, "Team not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(team, key, value)
    db.commit()
    db.refresh(team)
    return team


@router.delete("/{uid}", status_code=204)
def delete_team(uid: str, db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.uid == uid).first()
    if not team:
        raise HTTPException(404, "Team not found")
    db.delete(team)
    db.commit()
