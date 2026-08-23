import os
import traceback

from sqlalchemy import select, update

from open_hoops.analyzer import OpenHoop
from open_hoops.core.database import Database
from open_hoops.core.logger.game import GameLogger
from open_hoops.core.logger.protocol import LoggerProtocol
from open_hoops.service.analysis.models import Roster, TeamRoster, Video
from open_hoops.service.event.models import EventSource, GameEvent
from open_hoops.service.game.models import Game, GameStatus
from open_hoops.service.player.models import Player  # noqa: F401
from open_hoops.service.stats.models import GamePlayerStats, GameTeamStats
from worker.celery_app import celery

database_url = os.environ.get(
    "OPEN_HOOPS_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/open_hoops"
)
database = Database(database_url)


@celery.task(name="worker.tasks.analyze_game")
def analyze_game(game_uid: str) -> None:
    with database.use_scoped_session() as session:
        game = session.scalars(select(Game).where(Game.uid == game_uid)).one()

        logger = GameLogger(database=database, game_id=game.id)

        try:
            _run_analysis(game, logger)
        except Exception:  # noqa: BLE001
            logger.error(f"Analysis failed:\n{traceback.format_exc()}")
            with database.use_scoped_session() as scoped_session:
                scoped_session.execute(
                    update(Game).where(Game.id == game.id).values(status=GameStatus.failed)
                )


def _run_analysis(game: Game, logger: LoggerProtocol) -> None:
    with database.use_scoped_session() as session:
        session.execute(update(Game).where(Game.id == game.id).values(status=GameStatus.processing))

    logger.info("Analysis started")

    own_players = [player for player in game.own_team.players]
    opponent_players = [player for player in game.opponent_team.players]

    roster = Roster(
        home=TeamRoster(
            color=game.own_team_color,
            players=[p.jersey_number for p in own_players],
        ),
        away=TeamRoster(
            color=game.opponent_team_color,
            players=[p.jersey_number for p in opponent_players],
        ),
    )

    file_paths = [game_file.file_path for game_file in game.files]
    logger.info(f"Processing {len(file_paths)} video file(s)")

    total_duration = 0.0
    fps = 0.0
    all_team_stats: dict[str, dict] = {}
    all_player_stats: dict[tuple[str, int], dict] = {}
    all_events = []
    frame_offset = 0

    for i, file_path in enumerate(file_paths, 1):
        logger.info(f"Analyzing file {i}/{len(file_paths)}: {os.path.basename(file_path)}")
        oh = OpenHoop(Video(path=file_path), roster=roster, logger=logger)
        stats = oh.extract_stats()
        logger.info(f"File {i} complete: {stats.duration_seconds:.1f}s, {len(stats.events)} events")

        total_duration += stats.duration_seconds
        fps = stats.fps

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
            ev_dict = {
                "type": event.type,
                "frame": event.frame + frame_offset,
                "timestamp_sec": event.timestamp_sec + (total_duration - stats.duration_seconds),
                "team_id": event.team_id,
                "player_id": event.player_id,
                "bbox": event.bbox,
            }
            all_events.append(ev_dict)

        frame_offset += int(stats.duration_seconds * stats.fps)

    game.duration_seconds = total_duration
    game.fps = fps
    logger.info(
        f"All files processed. Saving results: {len(all_team_stats)} teams,"
        f" {len(all_player_stats)} players, {len(all_events)} events"
    )

    player_map = {}
    for p in own_players + opponent_players:
        player_map[(p.team_id, p.jersey_number)] = p

    for key, ts in all_team_stats.items():
        team_id = game.own_team_id if key == "team_a" else game.opponent_team_id
        avg_poss = ts["possession_pct"] / ts["count"] if ts["count"] else 0
        with database.use_scoped_session() as session:
            session.add(
                GameTeamStats(
                    game_id=game.id,
                    team_id=team_id,
                    score=ts["score"],
                    possession_pct=avg_poss,
                )
            )

    unmatched_jerseys = []
    for (team_key, jersey), ps in all_player_stats.items():
        team_id = game.own_team_id if team_key == "team_a" else game.opponent_team_id
        player = player_map.get((team_id, jersey))
        if not player:
            unmatched_jerseys.append(jersey)
        with database.use_scoped_session() as session:
            session.add(
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

    if unmatched_jerseys:
        logger.warning(f"Unmatched jersey numbers (not in roster): {unmatched_jerseys}")
    logger.info(f"Saving {len(all_events)} game events")

    for ev in all_events:
        team_id = None
        if ev["team_id"] == "team_a":
            team_id = game.own_team_id
        elif ev["team_id"] == "team_b":
            team_id = game.opponent_team_id

        player = None
        if ev["player_id"] is not None and team_id is not None:
            player = player_map.get((team_id, ev["player_id"]))

        bbox = ev["bbox"]

        with database.use_scoped_session() as session:
            session.add(
                GameEvent(
                    game_id=game.id,
                    type=ev["type"],
                    frame=ev["frame"],
                    timestamp_sec=ev["timestamp_sec"],
                    player_id=player.id if player else None,
                    team_id=team_id,
                    source=EventSource.analysis,
                    bbox_x1=bbox.x1 if bbox else None,
                    bbox_y1=bbox.y1 if bbox else None,
                    bbox_x2=bbox.x2 if bbox else None,
                    bbox_y2=bbox.y2 if bbox else None,
                )
            )

    with database.use_scoped_session() as session:
        session.execute(update(Game).where(Game.id == game.id).values(status=GameStatus.done))

    logger.info(f"Analysis complete: {total_duration:.1f}s total, {len(all_events)} events")
