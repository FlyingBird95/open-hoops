from app.celery_app import celery
from app.database import SessionLocal
from app.models import Video, Player, VideoStatus


@celery.task(name="app.tasks.analyze_video")
def analyze_video(video_uid: str) -> None:
    # Defer open_hoops imports to task execution time to avoid cv2 at import
    from open_hoops import OpenHoop, Roster, TeamRoster
    from open_hoops.models import Video as OHVideo

    db = SessionLocal()
    try:
        video = db.query(Video).filter(Video.uid == video_uid).first()
        if not video:
            return

        video.status = VideoStatus.processing
        db.commit()

        home_players = db.query(Player).filter(Player.team_id == video.home_team_id).all()
        away_players = db.query(Player).filter(Player.team_id == video.away_team_id).all()

        roster = Roster(
            home=TeamRoster(
                color=video.home_team.home_color,
                players=[p.jersey_number for p in home_players],
            ),
            away=TeamRoster(
                color=video.away_team.away_color,
                players=[p.jersey_number for p in away_players],
            ),
        )

        oh = OpenHoop(OHVideo(path=video.file_path), roster=roster)
        stats = oh.extract_stats()

        video.stats_json = stats.model_dump()
        video.status = VideoStatus.done
        db.commit()
    except Exception:
        video.status = VideoStatus.failed
        db.commit()
    finally:
        db.close()
