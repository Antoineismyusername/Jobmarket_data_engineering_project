import base64
import os

from fastapi.testclient import TestClient

from api.main import app

os.environ["API_USERNAME"] = "testuser"
os.environ["API_PASSWORD"] = "testpass"


client = TestClient(app)

credentials = base64.b64encode(b"testuser:testpass").decode("utf-8")
AUTH_HEADERS = {"Authorization": f"Basic {credentials}"}


def test_home():
    response = client.get("/", headers=AUTH_HEADERS)
    assert response.status_code == 200

def test_wrong_authentication():
    wrong_credentials = base64.b64encode(b"wronguser:wrongpassword").decode("utf-8")

    wrong_headers = {"Authorization": f"Basic {wrong_credentials}"}

    response = client.post(
        "/offers/city", 
        json={"city": "montpellier", "limit": 10},
        headers=wrong_headers)

    assert response.status_code == 422

def test_offers_by_city():
    response = client.post(
        "/offers/city",
        json={"city": "montpellier", "limit": 10},
        headers=AUTH_HEADERS,
    )

    data = response.json()

    assert response.status_code == 200
    assert "count" in data
    assert data["count"] <= 10