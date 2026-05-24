import pytest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/postgres"
)

from gateway.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_predict_returns_valid_response():
    response = client.post("/predict", json={"text": "I love this product"})
    assert response.status_code == 200
    data = response.json()
    assert "prediction" in data
    assert "model_a" in data
    assert "model_b" in data
    assert "agreed" in data
    assert "agreement_rate" in data
    assert data["prediction"] in ["positive", "negative", "neutral"]

def test_predict_negative_sentiment():
    response = client.post("/predict", json={"text": "This is absolutely terrible"})
    assert response.status_code == 200
    data = response.json()
    assert data["model_a"]["label"] == "negative"

def test_predict_positive_sentiment():
    response = client.post("/predict", json={"text": "This is absolutely amazing"})
    assert response.status_code == 200
    data = response.json()
    assert data["model_a"]["label"] == "positive"

def test_stats_returns_valid_structure():
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert "agreement_rate" in data
    assert "total" in data
    assert "disagreements" in data
    assert "diagnosis" in data
    assert "chart_data" in data
    assert "recent" in data

def test_predict_invalid_request():
    response = client.post("/predict", json={})
    assert response.status_code == 422