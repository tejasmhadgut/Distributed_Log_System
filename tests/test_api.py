import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from src.main import app
from src.database import search_logs, insert_logs
from src.models.log import Log

client = TestClient(app)

def test_health():
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_ingest_single_log():
    """Test ingesting a single log."""
    log_data = {
        "timestamp": "2026-05-23T12:00:00Z",
        "service_name": "test-service",
        "log_level": "INFO",
        "message": "Test message"
    }
    response = client.post("/logs/ingest", json=[log_data])
    assert response.status_code == 200
    assert response.json()["inserted"] == 1

def test_ingest_multiple_logs():
    """Test ingesting multiple logs."""
    logs = [
        {
            "timestamp": "2026-05-23T12:00:00Z",
            "service_name": "service-1",
            "log_level": "ERROR",
            "message": "Error 1"
        },
        {
            "timestamp": "2026-05-23T12:01:00Z",
            "service_name": "service-2",
            "log_level": "WARN",
            "message": "Warning"
        }
    ]
    response = client.post("/logs/ingest", json=logs)
    assert response.status_code == 200
    assert response.json()["inserted"] == 2

def test_ingest_invalid_log_level():
    """Test that invalid log level is rejected."""
    log_data = {
        "timestamp": "2026-05-23T12:00:00Z",
        "service_name": "test-service",
        "log_level": "INVALID",  # Should fail validation
        "message": "Test"
    }
    response = client.post("/logs/ingest", json=[log_data])
    assert response.status_code == 422  # Unprocessable Entity

def test_search_by_service():
    """Test searching logs by service."""
    response = client.get("/logs/search?service=auth-service")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "source" in data

def test_search_with_filters():
    """Test searching with level filter."""
    response = client.get("/logs/search?service=auth-service&level=ERROR&hours=24")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["results"], list)

def test_search_nonexistent_service():
    """Test searching for service that doesn't exist."""
    response = client.get("/logs/search?service=nonexistent-service")
    assert response.status_code == 200
    assert response.json()["results"] == []
