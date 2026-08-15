from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


class Point(BaseModel):
    x: float
    y: float


class Video(BaseModel):
    path: str

    def __init__(self, path: str | None = None, **data):
        if path is not None:
            data["path"] = path
        super().__init__(**data)


class TeamRoster(BaseModel):
    color: str
    players: list[int] = Field(default_factory=list)


class Roster(BaseModel):
    home: TeamRoster
    away: TeamRoster


class PlayerStats(BaseModel):
    player_id: int | None
    team_id: str
    positions: list[Point] = Field(default_factory=list)
    distance_covered_m: float = 0.0
    game_time_seconds: float = 0.0
    shot_attempts: int = 0
    shot_makes: int = 0
    passes_made: int = 0
    passes_received: int = 0
    possession_frames: int = 0


class TeamStats(BaseModel):
    team_id: str
    color: str = ""
    score: int = 0
    players: list[PlayerStats] = Field(default_factory=list)
    possession_pct: float = 0.0


class SubstitutionEvent(BaseModel):
    track_id: int
    team_id: str | None = None
    jersey: int | None = None
    frame_on: int
    frame_off: int | None = None


class GameEvent(BaseModel):
    type: Literal["shot", "make", "miss", "pass", "possession_change"]
    frame: int
    timestamp_sec: float
    player_id: int | None = None
    team_id: str | None = None


class GameStats(BaseModel):
    video: Video
    duration_seconds: float
    fps: float
    teams: list[TeamStats] = Field(default_factory=list)
    events: list[GameEvent] = Field(default_factory=list)
    substitutions: list[SubstitutionEvent] = Field(default_factory=list)
