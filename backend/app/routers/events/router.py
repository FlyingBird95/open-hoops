from fastapi import APIRouter

router = APIRouter(prefix="/api/events", tags=["events"])

from . import collection, delete, frame, get, patch, post
