from fastapi import APIRouter

router = APIRouter(prefix="/api/games", tags=["games"])

from . import collection, files, get, patch, post, stats
