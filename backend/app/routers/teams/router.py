from fastapi import APIRouter

router = APIRouter(prefix="/api/teams", tags=["teams"])

from . import collection, delete, get, patch, post
