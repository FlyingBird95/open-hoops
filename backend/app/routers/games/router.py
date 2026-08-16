from fastapi import APIRouter

from .collection import list_games
from .events_delete import delete_event
from .events_post import create_event
from .files import list_game_files
from .frame import get_event_frame
from .get import get_game
from .patch import update_game
from .post import upload_game
from .stats import get_game_events, get_game_stats

router = APIRouter(prefix="/api/games", tags=["games"])
router.get("")(list_games)
router.post("")(upload_game)
router.get("/{uid}")(get_game)
router.patch("/{uid}")(update_game)
router.get("/{uid}/stats")(get_game_stats)
router.get("/{uid}/events")(get_game_events)
router.post("/{uid}/events")(create_event)
router.delete("/{uid}/events/{event_id}")(delete_event)
router.get("/{uid}/files")(list_game_files)
router.get("/{uid}/events/{event_id}/frame")(get_event_frame)
