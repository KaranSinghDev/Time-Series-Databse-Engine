import os
import shutil
import pytest  # --- FIX: Import the pytest library ---
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
DATA_DIRECTORY = "data"

# This is a pytest fixture. It's a modern and clean way to handle setup/teardown.
# The 'autouse=True' means it will automatically run for every test function.
@pytest.fixture(autouse=True)
def clean_database_before_and_after_each_test():
    """Ensure the database directory is clean before and after each test."""
    if os.path.exists(DATA_DIRECTORY):
        shutil.rmtree(DATA_DIRECTORY)
    
    yield  # This is the point where the actual test runs.

    if os.path.exists(DATA_DIRECTORY):
        shutil.rmtree(DATA_DIRECTORY)

def test_ingest_endpoint_success():
    """Tests the /api/ingest endpoint for successful data point ingestion."""
    response = client.post("/api/ingest", json={
        "metric": "cpu.test.load",
        "timestamp": 1700000000000,
        "value": 99.9
    })
    assert response.status_code == 200
    assert os.path.isdir(DATA_DIRECTORY)
    shard_files = os.listdir(DATA_DIRECTORY)
    assert len(shard_files) > 0
    # Check that the file has content (proving compression works, size > 0)
    assert os.path.getsize(os.path.join(DATA_DIRECTORY, shard_files[0])) > 0

def test_query_endpoint():
    """
    Tests the /api/query endpoint by first ingesting data and then querying it.
    """
    # Arrange: Ingest some known data points.
    client.post("/api/ingest", json={"metric": "test", "timestamp": 100, "value": 10.0})
    client.post("/api/ingest", json={"metric": "test", "timestamp": 150, "value": 15.0})
    client.post("/api/ingest", json={"metric": "test", "timestamp": 200, "value": 20.0})
    client.post("/api/ingest", json={"metric": "test", "timestamp": 300, "value": 30.0})

    # Act: Query for a specific time range.
    response = client.get("/api/query?start_ts=100&end_ts=250")

    # Assert: Check the response is correct.
    assert response.status_code == 200
    data = response.json()
    assert data["metric"] == "cpu.load.avg"
    assert len(data["points"]) == 3
    assert data["points"][0] == {"timestamp": 100, "value": 10.0}
    assert data["points"][1] == {"timestamp": 150, "value": 15.0}
    assert data["points"][2] == {"timestamp": 200, "value": 20.0}

def test_query_endpoint_empty_result():
    """Tests the /api/query endpoint for a time range with no data."""
    # The fixture ensures the database is empty before this test.
    response = client.get("/api/query?start_ts=100&end_ts=250")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["points"]) == 0