import os

from worker.celery_app import celery
from open_hoops.db import (
    get_session_factory,
    Game,
    Player,
    GameStatus,
    GameTeamStats,
    GamePlayerStats,
    GameEvent,
)

database_url = os.environ.get(
    "OPEN_HOOPS_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/open_hoops"
)
SessionLocal = get_session_factory(database_url)


@celery.task(name="worker.tasks.analyze_game")
def analyze_game(game_uid: str) -> None:
    from open_hoops import OpenHoop, Roster, TeamRoster
    from open_hoops.models import Video as OHVideo

    db = SessionLocal()
    try:
        game = db.query(Game).filter(Game.uid == game_uid).first()
        if not game:
            return

        game.status = GameStatus.processing
        db.commit()

        home_players = db.query(Player).filter(Player.team_id == game.home_team_id).all()
        away_players = db.query(Player).filter(Player.team_id == game.away_team_id).all()

        roster = Roster(
            home=TeamRoster(
                color=game.home_team_color,
                players=[p.jersey_number for p in home_players],
            ),
            away=TeamRoster(
                color=game.away_team_color,
                players=[p.jersey_number for p in away_players],
            ),
        )

        oh = OpenHoop(OHVideo(path=game.file_path), roster=roster)
        stats = oh.extract_stats()

        game.duration_seconds = stats.duration_seconds
        game.fps = stats.fps

        player_map = {}
        for p in home_players + away_players:
            player_map[(p.team_id, p.jersey_number)] = p

        for team_stat in stats.teams:
            team_id = game.home_team_id if team_stat.team_id == "home" else game.away_team_id
            db.add(
                GameTeamStats(
                    game_id=game.id,
                    team_id=team_id,
                    score=team_stat.score,
                    possession_pct=team_stat.possession_pct,
                )
            )

            for ps in team_stat.players:
                player = player_map.get((team_id, ps.player_id))
                db.add(
                    GamePlayerStats(
                        game_id=game.id,
                        team_id=team_id,
                        player_id=player.id if player else None,
                        jersey_number=ps.player_id,
                        distance_covered_m=ps.distance_covered_m,
                        shot_attempts=ps.shot_attempts,
                        shot_makes=ps.shot_makes,
                        passes_made=ps.passes_made,
                        passes_received=ps.passes_received,
                        possession_frames=ps.possession_frames,
                    )
                )

        for event in stats.events:
            team_id = None
            if event.team_id == "home":
                team_id = game.home_team_id
            elif event.team_id == "away":
                team_id = game.away_team_id

            player = None
            if event.player_id is not None and team_id is not None:
                player = player_map.get((team_id, event.player_id))

            db.add(
                GameEvent(
                    game_id=game.id,
                    type=event.type,
                    frame=event.frame,
                    timestamp_sec=event.timestamp_sec,
                    player_id=player.id if player else None,
                    team_id=team_id,
                )
            )

        game.status = GameStatus.done
        db.commit()
    except Exception:
        db.rollback()
        game.status = GameStatus.failed
        db.commit()
    finally:
        db.close()
