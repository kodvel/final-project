from fastapi import FastAPI

app = FastAPI(title="Final Project API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "api"}
