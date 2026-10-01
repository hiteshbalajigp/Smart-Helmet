"""Integration tests for FastAPI backend."""

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app


@pytest.fixture
async def client(test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_upload_and_list_violation(client):
    payload = {
        "violation_id": "test-uuid-001",
        "violation_type": "no_helmet",
        "timestamp": "2026-06-27T10:00:00Z",
        "track_id": 1,
        "confidence": 0.91,
        "plate_text": "DL01AB1234",
        "device_id": "HELMET-TEST",
        "gps": {"latitude": 28.6139, "longitude": 77.2090},
        "metadata": {},
        "evidence": {"snapshot": "evidence/test.jpg", "video": "evidence/test.mp4"},
    }
    create_resp = await client.post("/api/v1/violations", json=payload)
    assert create_resp.status_code == 201

    list_resp = await client.get("/api/v1/violations")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["total"] >= 1

    search_resp = await client.get("/api/v1/violations/search", params={"plate": "DL01"})
    assert search_resp.status_code == 200

    stats_resp = await client.get("/api/v1/dashboard/stats")
    assert stats_resp.status_code == 200
    assert "total_violations" in stats_resp.json()
