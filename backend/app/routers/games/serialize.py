from app.models import Game, GameTeamStats, GamePlayerStats, GameEvent
from app.jsonapi import resource_object, relationship_linkage


def serialize_game(game: Game) -> dict:
    return resource_object(
        type="games",
        uid=game.uid,
        attributes={
            "name": game.name,
            "date": game.date.isoformat(),
            "home_team_color": game.home_team_color,
            "away_team_color": game.away_team_color,
            "duration_seconds": game.duration_seconds,
            "fps": game.fps,
            "status": game.status.value,
        },
        relationships={
            "home_team": relationship_linkage("teams", game.home_team.uid),
            "away_team": relationship_linkage("teams", game.away_team.uid),
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

    return resource_object(
        type="game_events",
        uid=str(ev.id),
        attributes={
            "type": ev.type,
            "frame": ev.frame,
            "timestamp_sec": ev.timestamp_sec,
        },
        relationships=rels,
    )
