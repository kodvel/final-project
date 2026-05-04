from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference
from sqlmodel import Session

from app.core.config import get_settings
from app.db.session import engine, init_db
from app.routes import chat, decision_briefs, sources, visualizations, workspaces
from app.services.workspaces import seed_default_workspaces

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with Session(engine) as session:
        seed_default_workspaces(session)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(workspaces.router)
app.include_router(sources.router)
app.include_router(visualizations.router)
app.include_router(chat.router)
app.include_router(decision_briefs.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "api"}


@app.get("/scalar", include_in_schema=False)
def scalar_html():
    return get_scalar_api_reference(openapi_url=app.openapi_url, title=f"{settings.app_name} Docs")
