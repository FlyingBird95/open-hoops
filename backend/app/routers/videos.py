import os
import shutil

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Team, Video, generate_uid
from app.schemas.videos import VideoResponse
from app.tasks import analyze_video
from datetime import date as date_type

router = APIRouter(prefix="/api/videos", tags=["videos"])


def _video_response(video: Video) -> dict:
    return {
        "uid": video.uid,
        "name": video.name,
        "date": video.date,
        "home_team_uid": video.home_team.uid,
        "away_team_uid": video.away_team.uid,
        "status": video.status.value,
        "stats_json": video.stats_json,
    }


@router.post("", response_model=VideoResponse, status_code=201)
def upload_video(
    name: str = Form(...),
    date: date_type = Form(...),
    home_team_uid: str = Form(...),
    away_team_uid: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    home_team = db.query(Team).filter(Team.uid == home_team_uid).first()
    if not home_team:
        raise HTTPException(404, "Home team not found")
    away_team = db.query(Team).filter(Team.uid == away_team_uid).first()
    if not away_team:
        raise HTTPException(404, "Away team not found")

    os.makedirs(settings.upload_dir, exist_ok=True)
    uid = generate_uid()
    ext = os.path.splitext(file.filename or "video.mp4")[1]
    file_path = os.path.join(settings.upload_dir, f"{uid}{ext}")

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    video = Video(
        uid=uid,
        name=name,
        date=date,
        file_path=file_path,
        home_team_id=home_team.id,
        away_team_id=away_team.id,
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    analyze_video.delay(video.uid)

    return _video_response(video)


@router.get("", response_model=list[VideoResponse])
def list_videos(db: Session = Depends(get_db)):
    videos = db.query(Video).order_by(Video.date.desc()).all()
    return [_video_response(v) for v in videos]


@router.get("/{uid}", response_model=VideoResponse)
def get_video(uid: str, db: Session = Depends(get_db)):
    video = db.query(Video).filter(Video.uid == uid).first()
    if not video:
        raise HTTPException(404, "Video not found")
    return _video_response(video)
