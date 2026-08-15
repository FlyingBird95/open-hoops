import os

from app.models import Game, GameFile, GameTeamStats, GamePlayerStats, GameEvent
from app.jsonapi import resource_object, relationship_linkage


def serialize_game(game: Game) -> dict:
    return resource_object(
        type="games",
        uid=game.uid,
        attributes={
            "name": game.name,
            "date": game.date.isoformat(),
            "own_team_color": game.own_team_color,
            "opponent_team_color": game.opponent_team_color,
            "duration_seconds": game.duration_seconds,
            "fps": game.fps,
            "status": game.status.value,
            "file_count": len(game.files),
            "is_archived": game.is_archived,
        },
        relationships={
            "own_team": relationship_linkage("teams", game.own_team.uid),
            "opponent_team": relationship_linkage("teams", game.opponent_team.uid),
        },
    )


def serialize_game_file(gf: GameFile) -> dict:
    filename = os.path.basename(gf.file_path)
    return resource_object(
        type="game_files",
        uid=gf.uid,
        attributes={
            "original_filename": gf.original_filename,
            "position": gf.position,
            "size_bytes": gf.size_bytes,
            "url": f"/uploads/{filename}",
        },
        relationships={
            "game": relationship_linkage("games", gf.game.uid),
        },
    )


def serialize_team_stats(ts: GameTeamStats) -> dict:
    return resource_object(
        type="game_team_stats",
        uid=str(ts.id),
        attributes={
            "score": ts.score,
            "possession_pct": ts.possession_pct,
        },
        relationships={
            "team": relationship_linkage("teams", ts.team.uid),
            "game": relationship_linkage("games", ts.game.uid),
        },
    )


def serialize_player_stats(ps: GamePlayerStats) -> dict:
    rels: dict = {
        "team": relationship_linkage("teams", ps.team.uid),
        "game": relationship_linkage("games", ps.game.uid),
    }
    if ps.player:
        rels["player"] = relationship_linkage("players", ps.player.uid)

    return resource_object(
        type="game_player_stats",
        uid=str(ps.id),
        attributes={
            "jersey_number": ps.jersey_number,
            "distance_covered_m": ps.distance_covered_m,
            "shot_attempts": ps.shot_attempts,
            "shot_makes": ps.shot_makes,
            "passes_made": ps.passes_made,
            "passes_received": ps.passes_received,
            "possession_frames": ps.possession_frames,
        },
        relationships=rels,
    )


def serialize_event(ev: GameEvent) -> dict:
    rels: dict = {"game": relationship_linkage("games", ev.game.uid)}
    if ev.team:
        rels["team"] = relationship_linkage("teams", ev.team.uid)
    if ev.player:
        rels["player"] = relationship_linkage("players", ev.player.uid)

    bbox = None
    if ev.bbox_x1 is not None:
        bbox = {"x1": ev.bbox_x1, "y1": ev.bbox_y1, "x2": ev.bbox_x2, "y2": ev.bbox_y2}

    return resource_object(
        type="game_events",
        uid=str(ev.id),
        attributes={
            "type": ev.type,
            "frame": ev.frame,
            "timestamp_sec": ev.timestamp_sec,
            "bbox": bbox,
        },
        relationships=rels,
    )
