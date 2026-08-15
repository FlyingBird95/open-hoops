from fastapi import APIRouter

from .collection import list_players
from .delete import delete_player
from .get import get_player
from .patch import update_player
from .post import create_player

router = APIRouter(prefix="/api/players", tags=["players"])
router.get("")(list_players)
router.post("")(create_player)
router.get("/{uid}")(get_player)
router.patch("/{uid}")(update_player)
router.delete("/{uid}")(delete_player)
