import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.api.routes import resume, upload
from app.core.config import settings
from app.core.database import engine, init_db
from app.models.user import User

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)


def _ensure_demo_user() -> None:
    with Session(engine) as session:
        if session.query(User).first() is not None:
            return
        session.add(User(email="demo@example.com", full_name="Demo User"))
        session.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    _ensure_demo_user()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan, debug=settings.debug)

app.include_router(upload.router)
app.include_router(resume.router)

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/assets", StaticFiles(directory=frontend_dir), name="frontend-assets")


@app.get("/", response_model=None)
def frontend():
    index_file = frontend_dir / "index.html"
    if not index_file.exists():
        return JSONResponse(
            status_code=404,
            content={"detail": "Frontend not found. Create frontend/index.html"},
        )
    return FileResponse(index_file)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
