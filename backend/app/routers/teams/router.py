from fastapi import APIRouter

from .collection import list_teams
from .post import create_team
from .get import get_team
from .patch import update_team
from .delete import delete_team

router = APIRouter(prefix="/api/teams", tags=["teams"])
router.get("")(list_teams)
router.post("")(create_team)
router.get("/{uid}")(get_team)
router.patch("/{uid}")(update_team)
router.delete("/{uid}")(delete_team)
