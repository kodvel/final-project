import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference
from sqlmodel import Session

from app.core.config import get_settings
from app.db.session import engine
from app.mcp.server import mcp_app as fastmcp_app
from app.routes import chat, decision_briefs, sources, visualizations, workspaces
from app.services.workspaces import seed_default_workspaces

settings = get_settings()


def _configure_langfuse() -> bool:
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return False

    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
    os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
    os.environ.setdefault("LANGFUSE_BASE_URL", settings.langfuse_host)
    return True


mcp_streamable_app = fastmcp_app.streamable_http_app()


@asynccontextmanager
async def lifespan(app: FastAPI):
    langfuse_client = None
    if _configure_langfuse():
        from langfuse import get_client
        from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor

        langfuse_client = get_client()
        OpenAIAgentsInstrumentor().instrument()

    with Session(engine) as session:
        seed_default_workspaces(session)

    async with fastmcp_app.session_manager.run():
        yield

    if langfuse_client:
        langfuse_client.shutdown()


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

app.mount("/mcp", mcp_streamable_app)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "api"}


@app.get("/scalar", include_in_schema=False)
def scalar_html():
    return get_scalar_api_reference(openapi_url=app.openapi_url, title=f"{settings.app_name} Docs")
