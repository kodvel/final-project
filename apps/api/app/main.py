from fastapi import FastAPI
from scalar_fastapi import get_scalar_api_reference

from app.core.config import get_settings
from app.routes import chat, decision_briefs, sources, visualizations, workspaces

settings = get_settings()

app = FastAPI(title=settings.app_name)

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
