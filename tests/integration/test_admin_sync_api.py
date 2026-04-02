from fastapi.testclient import TestClient

from agentgw.bootstrap.gateway_app import create_app


def test_admin_sync_endpoint_accepts_request() -> None:
    client = TestClient(create_app())

    response = client.post("/admin/sync/messages", json={"account_id": "acc-1"})

    assert response.status_code == 202
    assert response.json() == {"accepted": True, "account_id": "acc-1"}


def test_admin_sync_endpoint_rejects_unknown_channel_type() -> None:
    client = TestClient(create_app())

    response = client.post("/admin/sync/messages", json={"account_id": "acc-1", "channel_type": "unknown"})

    assert response.status_code == 400
    assert response.json() == {"detail": "unsupported channel_type: unknown"}
