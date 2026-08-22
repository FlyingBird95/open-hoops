from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from open_hoops.core.database import get_engine, get_session_factory

get_engine(settings.database_url)
get_session_factory(settings.database_url)

from app.routers.events.router import router as events_router
from app.routers.games.router import router as games_router
from app.routers.players.router import router as players_router
from app.routers.teams.router import router as teams_router

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
