from fastapi import APIRouter

router = APIRouter(prefix="/api/players", tags=["players"])

from . import collection, delete, get, patch, post
