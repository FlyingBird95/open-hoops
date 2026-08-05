import os

from worker.celery_app import celery
from open_hoops.db import (
    get_session_factory,
    Game,
    GameFile,
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

        game_files = (
            db.query(GameFile).filter(GameFile.game_id == game.id).order_by(GameFile.position).all()
        )

        # Fallback for legacy games with file_path but no GameFile rows
        if not game_files and game.file_path:
            file_paths = [game.file_path]
        else:
            file_paths = [gf.file_path for gf in game_files]

        total_duration = 0.0
        fps = 0.0
        all_team_stats: dict[str, dict] = {}
        all_player_stats: dict[tuple[str, int], dict] = {}
        all_events = []
        frame_offset = 0

        for file_path in file_paths:
            oh = OpenHoop(OHVideo(path=file_path), roster=roster)
            stats = oh.extract_stats()

            total_duration += stats.duration_seconds
            fps = stats.fps  # use fps from last segment (should be consistent)

            for team_stat in stats.teams:
                key = team_stat.team_id
                if key not in all_team_stats:
                    all_team_stats[key] = {"score": 0, "possession_pct": 0.0, "count": 0}
                all_team_stats[key]["score"] += team_stat.score
                all_team_stats[key]["possession_pct"] += team_stat.possession_pct
                all_team_stats[key]["count"] += 1

                for ps in team_stat.players:
                    pkey = (key, ps.player_id)
                    if pkey not in all_player_stats:
                        all_player_stats[pkey] = {
                            "player_id": ps.player_id,
                            "team_id": key,
                            "distance_covered_m": 0.0,
                            "shot_attempts": 0,
                            "shot_makes": 0,
                            "passes_made": 0,
                            "passes_received": 0,
                            "possession_frames": 0,
                        }
                    s = all_player_stats[pkey]
                    s["distance_covered_m"] += ps.distance_covered_m
                    s["shot_attempts"] += ps.shot_attempts
                    s["shot_makes"] += ps.shot_makes
                    s["passes_made"] += ps.passes_made
                    s["passes_received"] += ps.passes_received
                    s["possession_frames"] += ps.possession_frames

            for event in stats.events:
                all_events.append(
                    {
                        "type": event.type,
                        "frame": event.frame + frame_offset,
                        "timestamp_sec": event.timestamp_sec
                        + (total_duration - stats.duration_seconds),
                        "team_id": event.team_id,
                        "player_id": event.player_id,
                    }
                )

            frame_offset += int(stats.duration_seconds * stats.fps)

        game.duration_seconds = total_duration
        game.fps = fps

        player_map = {}
        for p in home_players + away_players:
            player_map[(p.team_id, p.jersey_number)] = p

        for key, ts in all_team_stats.items():
            team_id = game.home_team_id if key == "home" else game.away_team_id
            avg_poss = ts["possession_pct"] / ts["count"] if ts["count"] else 0
            db.add(
                GameTeamStats(
                    game_id=game.id,
                    team_id=team_id,
                    score=ts["score"],
                    possession_pct=avg_poss,
                )
            )

        for (team_key, jersey), ps in all_player_stats.items():
            team_id = game.home_team_id if team_key == "home" else game.away_team_id
            player = player_map.get((team_id, jersey))
            db.add(
                GamePlayerStats(
                    game_id=game.id,
                    team_id=team_id,
                    player_id=player.id if player else None,
                    jersey_number=jersey,
                    distance_covered_m=ps["distance_covered_m"],
                    shot_attempts=ps["shot_attempts"],
                    shot_makes=ps["shot_makes"],
                    passes_made=ps["passes_made"],
                    passes_received=ps["passes_received"],
                    possession_frames=ps["possession_frames"],
                )
            )

        for ev in all_events:
            team_id = None
            if ev["team_id"] == "home":
                team_id = game.home_team_id
            elif ev["team_id"] == "away":
                team_id = game.away_team_id

            player = None
            if ev["player_id"] is not None and team_id is not None:
                player = player_map.get((team_id, ev["player_id"]))

            db.add(
                GameEvent(
                    game_id=game.id,
                    type=ev["type"],
                    frame=ev["frame"],
                    timestamp_sec=ev["timestamp_sec"],
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
