"""mybro FastAPI backend — project management + ticketing + dashboard."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import config
from backend.db import postgres, sqlite, redis
from backend.services import scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    await postgres.init_pool()
    await sqlite.init_db()
    await redis.init_redis()
    scheduler.start()
    yield
    scheduler.stop()
    await redis.close_redis()
    await sqlite.close_db()
    await postgres.close_pool()


app = FastAPI(title="mybro", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.server.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
from backend.api import projects, tickets, feed, dashboard, system, time_tracking, insights  # noqa: E402

app.include_router(projects.router, prefix="/api")
app.include_router(tickets.router, prefix="/api")
app.include_router(feed.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(system.router, prefix="/api")
app.include_router(time_tracking.router, prefix="/api")
app.include_router(insights.router, prefix="/api")


@app.get("/")
async def health():
    return {"status": "operational", "service": "mybro"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.server.host, port=config.server.port, reload=True)
