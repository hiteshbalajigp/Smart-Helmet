from fastapi.testclient import TestClient


def test_register_and_list_camera(client: TestClient, admin_token: str) -> None:
    headers = {"Authorization": f"Bearer {admin_token}"}
    create = client.post(
        "/api/v1/cameras",
        headers=headers,
        json={
            "camera_id": "CAM-TEST-01",
            "camera_name": "Test USB Camera",
            "location_name": "Test Junction",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "usb_device_index": 1,
            "is_authorized": True,
        },
    )
    assert create.status_code == 201
    assert create.json()["camera_id"] == "CAM-TEST-01"

    listing = client.get("/api/v1/cameras", headers=headers)
    assert listing.status_code == 200
    assert any(item["camera_id"] == "CAM-TEST-01" for item in listing.json())
