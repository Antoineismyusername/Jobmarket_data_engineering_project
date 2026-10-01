import base64
from unittest.mock import Mock

import pytest

from fastapi.testclient import TestClient

from api.main import app

@pytest.fixture(autouse=True)
def fake_database(monkeypatch):
    # Identifiants fictifs, valables uniquement pendant chaque test.
    monkeypatch.setenv("API_USERNAME", "testuser")
    monkeypatch.setenv("API_PASSWORD", "testpass")

    # Cette collection en mémoire remplace MongoDB pendant les tests.
    collection = Mock()
    collection.find.return_value = [
        {"title": "Développeur Python", "locationCity": "Montpellier"},
        {"title": "Data engineer", "locationCity": "Toulouse"},
        {"title": "Boulanger", "locationCity": "Montpellier"},
    ]

    # Remplacer la fonction à l'endroit où l'API l'utilise.
    # pytest annule automatiquement ce remplacement après chaque test.
    monkeypatch.setattr("api.main.get_collection", lambda: collection)


client = TestClient(app)

credentials = base64.b64encode(b"testuser:testpass").decode("utf-8")
AUTH_HEADERS = {"Authorization": f"Basic {credentials}"}


def test_home():
    response = client.get("/")
    assert response.status_code == 200

def test_wrong_authentication():
    wrong_credentials = base64.b64encode(b"wronguser:wrongpassword").decode("utf-8")

    wrong_headers = {"Authorization": f"Basic {wrong_credentials}"}

    response = client.post(
        "/offers/city",
        json={"city": "montpellier", "limit": 10},
        headers=wrong_headers,
    )

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
    assert all(offer["locationCity"] == "Montpellier" for offer in data["offers"])
