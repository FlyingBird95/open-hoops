import cv2
from fastapi import Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db, get_or_404
from open_hoops.service.event.models import GameEvent
from open_hoops.service.game.models import Game, GameFile


def get_event_frame(uid: str, event_id: int, db: Session = Depends(get_db)):
    game = get_or_404(db, Game, uid)

    event = (
        db.query(GameEvent).filter(GameEvent.id == event_id, GameEvent.game_id == game.id).first()
    )
    if not event:
        raise HTTPException(404, "Event not found")

    game_files = (
        db.query(GameFile).filter(GameFile.game_id == game.id).order_by(GameFile.position).all()
    )
    if not game_files:
        raise HTTPException(404, "No video files for game")

    target_frame = event.frame
    file_path = None
    local_frame = target_frame

    cumulative_frames = 0
    for gf in game_files:
        cap = cv2.VideoCapture(gf.file_path)
        if not cap.isOpened():
            cap.release()
            continue
        file_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        if target_frame < cumulative_frames + file_frames:
            file_path = gf.file_path
            local_frame = target_frame - cumulative_frames
            break
        cumulative_frames += file_frames

    if file_path is None:
        file_path = game_files[-1].file_path
        local_frame = target_frame - cumulative_frames

    cap = cv2.VideoCapture(file_path)
    if not cap.isOpened():
        cap.release()
        raise HTTPException(500, "Cannot open video file")

    cap.set(cv2.CAP_PROP_POS_FRAMES, local_frame)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise HTTPException(500, "Cannot read frame from video")

    if event.bbox_x1 is not None:
        cv2.rectangle(
            frame,
            (event.bbox_x1, event.bbox_y1),
            (event.bbox_x2, event.bbox_y2),
            (0, 255, 0),
            3,
        )
        label = event.type
        if event.player and event.player.jersey_number is not None:
            label = f"#{event.player.jersey_number} {label}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
        cv2.rectangle(
            frame,
            (event.bbox_x1, event.bbox_y1 - th - 10),
            (event.bbox_x1 + tw + 6, event.bbox_y1),
            (0, 255, 0),
            -1,
        )
        cv2.putText(
            frame,
            label,
            (event.bbox_x1 + 3, event.bbox_y1 - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 0),
            2,
        )

    _, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return Response(content=jpeg.tobytes(), media_type="image/jpeg")
