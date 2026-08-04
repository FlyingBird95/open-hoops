from fastapi import APIRouter

from .collection import list_games
from .post import upload_game
from .get import get_game
from .stats import get_game_stats, get_game_events

router = APIRouter(prefix="/api/games", tags=["games"])
router.get("")(list_games)
router.post("")(upload_game)
router.get("/{uid}")(get_game)
router.get("/{uid}/stats")(get_game_stats)
router.get("/{uid}/events")(get_game_events)
