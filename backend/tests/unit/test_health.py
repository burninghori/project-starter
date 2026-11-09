from fastapi.testclient import TestClient


def test_health_returns_ok_without_database(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_response_carries_request_id(client: TestClient) -> None:
    response = client.get("/api/health", headers={"x-request-id": "trace-abc_1"})

    assert response.headers["x-request-id"] == "trace-abc_1"


def test_malformed_request_id_is_replaced(client: TestClient) -> None:
    response = client.get("/api/health", headers={"x-request-id": "bad id with spaces"})

    assert response.headers["x-request-id"] != "bad id with spaces"
    assert len(response.headers["x-request-id"]) == 12
