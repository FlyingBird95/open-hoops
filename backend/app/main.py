from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import teams, players

app = FastAPI(title="Open Hoops API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(teams.router)
app.include_router(players.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
