from fastapi.testclient import TestClient

from app.main import app


def test_allows_local_web_origin_preflight() -> None:
    client = TestClient(app)

    response = client.options(
        "/workspaces",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_allows_local_web_origin_request() -> None:
    client = TestClient(app)

    response = client.get("/health", headers={"Origin": "http://localhost:3000"})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
