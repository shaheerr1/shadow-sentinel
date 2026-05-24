import pytest
import sys
import os
from unittest.mock import MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DATABASE_URL"] = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/postgres"
)

import gateway.main as main_module

main_module.model_a = MagicMock(
    return_value=[{"label": "POSITIVE", "score": 0.99}]
)
main_module.model_b = MagicMock(
    return_value=[{"label": "positive", "score": 0.98}]
)

from fastapi.testclient import TestClient
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

def test_predict_positive_sentiment():
    main_module.model_a = MagicMock(
        return_value=[{"label": "POSITIVE", "score": 0.99}]
    )
    main_module.model_b = MagicMock(
        return_value=[{"label": "positive", "score": 0.98}]
    )
    response = client.post("/predict", json={"text": "This is absolutely amazing"})
    assert response.status_code == 200
    data = response.json()
    assert data["model_a"]["label"] == "positive"

def test_predict_negative_sentiment():
    main_module.model_a = MagicMock(
        return_value=[{"label": "NEGATIVE", "score": 0.99}]
    )
    main_module.model_b = MagicMock(
        return_value=[{"label": "negative", "score": 0.97}]
    )
    response = client.post("/predict", json={"text": "This is absolutely terrible"})
    assert response.status_code == 200
    data = response.json()
    assert data["model_a"]["label"] == "negative"

def test_predict_disagreement():
    main_module.model_a = MagicMock(
        return_value=[{"label": "POSITIVE", "score": 0.95}]
    )
    main_module.model_b = MagicMock(
        return_value=[{"label": "negative", "score": 0.91}]
    )
    response = client.post("/predict", json={"text": "meh it was whatever"})
    assert response.status_code == 200
    data = response.json()
    assert data["agreed"] == False

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