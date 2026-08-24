import os

from open_hoops.service.game.models import Game, GameFile
from open_hoops.service.stats.models import GamePlayerStats, GameTeamStats

from app.jsonapi import relationship_linkage, resource_object


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
