import os
import shutil
from typing import List

from fastapi import Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.jsonapi import document
from app.models import Team, Game, GameFile, generate_uid
from app.celery_app import celery as celery_app
from datetime import date as date_type
from .serialize import serialize_game


def upload_game(
    name: str = Form(...),
    date: date_type = Form(...),
    home_team_uid: str = Form(...),
    away_team_uid: str = Form(...),
    home_team_color: str = Form("#000000"),
    away_team_color: str = Form("#ffffff"),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    home_team = db.query(Team).filter(Team.uid == home_team_uid).first()
    if not home_team:
        raise HTTPException(404, "Home team not found")
    away_team = db.query(Team).filter(Team.uid == away_team_uid).first()
    if not away_team:
        raise HTTPException(404, "Away team not found")

    os.makedirs(settings.upload_dir, exist_ok=True)
    game_uid = generate_uid()

    game = Game(
        uid=game_uid,
        name=name,
        date=date,
        file_path="",
        home_team_id=home_team.id,
        away_team_id=away_team.id,
        home_team_color=home_team_color,
        away_team_color=away_team_color,
    )
    db.add(game)
    db.flush()

    for position, upload_file in enumerate(files):
        file_uid = generate_uid()
        ext = os.path.splitext(upload_file.filename or "video.mp4")[1]
        file_path = os.path.join(settings.upload_dir, f"{file_uid}{ext}")

        with open(file_path, "wb") as f:
            shutil.copyfileobj(upload_file.file, f)

        size_bytes = os.path.getsize(file_path)

        game_file = GameFile(
            uid=file_uid,
            game_id=game.id,
            file_path=file_path,
            position=position,
            original_filename=upload_file.filename or "video.mp4",
            size_bytes=size_bytes,
        )
        db.add(game_file)

    db.commit()
    db.refresh(game)

    celery_app.send_task("worker.tasks.analyze_game", args=[game.uid])

    return JSONResponse(content=document(data=serialize_game(game)), status_code=201)
