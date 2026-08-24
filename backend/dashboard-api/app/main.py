import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import database  # noqa: F401
from app.routers.events.router import router as events_router
from app.routers.games.router import router as games_router
from app.routers.players.router import router as players_router
from app.routers.teams.router import router as teams_router

os.makedirs(settings.upload_dir, exist_ok=True)

app = FastAPI(title="Open Hoops API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(teams_router)
app.include_router(players_router)
app.include_router(games_router)
app.include_router(events_router)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")


@app.get("/api/health")
def health():
    return {"status": "ok"}
