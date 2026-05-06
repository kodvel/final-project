def create_workspace(client, name: str = "Chat Workspace") -> dict:
    response = client.post("/workspaces", json={"name": name, "description": "Chat test workspace"})
    assert response.status_code == 201
    return response.json()


def test_create_chat_session(client) -> None:
    workspace = create_workspace(client)

    response = client.post("/chat/sessions", json={"workspace_id": workspace["id"], "title": "Market strategy"})

    assert response.status_code == 201, response.text
    assert response.json()["workspace_id"] == workspace["id"]
    assert response.json()["title"] == "Market strategy"


def test_list_chat_sessions_scoped_by_workspace(client) -> None:
    first = create_workspace(client, "Workspace A")
    second = create_workspace(client, "Workspace B")
    first_session = client.post("/chat/sessions", json={"workspace_id": first["id"], "title": "A chat"}).json()
    client.post("/chat/sessions", json={"workspace_id": second["id"], "title": "B chat"})

    response = client.get(f"/chat/sessions?workspace_id={first['id']}")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [first_session["id"]]


def test_send_message_creates_user_and_assistant_messages(client) -> None:
    workspace = create_workspace(client)
    chat_session = client.post("/chat/sessions", json={"workspace_id": workspace["id"]}).json()

    response = client.post(
        f"/chat/sessions/{chat_session['id']}/messages?workspace_id={workspace['id']}",
        json={"content": "What should we do next quarter?"},
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["user_message"]["role"] == "user"
    assert payload["user_message"]["content"] == "What should we do next quarter?"
    assert payload["assistant_message"]["role"] == "assistant"
    assert "placeholder assistant response" in payload["assistant_message"]["content"]


def test_get_chat_session_returns_messages(client) -> None:
    workspace = create_workspace(client)
    chat_session = client.post("/chat/sessions", json={"workspace_id": workspace["id"]}).json()
    client.post(f"/chat/sessions/{chat_session['id']}/messages?workspace_id={workspace['id']}", json={"content": "Analyze churn risk"})

    response = client.get(f"/chat/sessions/{chat_session['id']}?workspace_id={workspace['id']}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["workspace_id"] == workspace["id"]
    assert payload["title"] == "Analyze churn risk"
    assert [message["role"] for message in payload["messages"]] == ["user", "assistant"]


def test_send_empty_message_is_rejected(client) -> None:
    workspace = create_workspace(client)
    chat_session = client.post("/chat/sessions", json={"workspace_id": workspace["id"]}).json()

    response = client.post(f"/chat/sessions/{chat_session['id']}/messages?workspace_id={workspace['id']}", json={"content": "   "})

    assert response.status_code == 400


def test_chat_session_detail_rejects_wrong_workspace(client) -> None:
    first = create_workspace(client, "Workspace A")
    second = create_workspace(client, "Workspace B")
    chat_session = client.post("/chat/sessions", json={"workspace_id": first["id"]}).json()

    response = client.get(f"/chat/sessions/{chat_session['id']}?workspace_id={second['id']}")

    assert response.status_code == 404


def test_send_message_rejects_wrong_workspace(client) -> None:
    first = create_workspace(client, "Workspace A")
    second = create_workspace(client, "Workspace B")
    chat_session = client.post("/chat/sessions", json={"workspace_id": first["id"]}).json()

    response = client.post(
        f"/chat/sessions/{chat_session['id']}/messages?workspace_id={second['id']}",
        json={"content": "Should not persist"},
    )

    assert response.status_code == 404
