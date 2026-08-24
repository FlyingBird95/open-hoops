from fastapi import APIRouter

router = APIRouter(prefix="/api/games", tags=["games"])

from . import collection, files, get, logs, patch, post, stats
