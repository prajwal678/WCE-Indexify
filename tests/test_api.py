import pytest
from httpx import AsyncClient
from main import app
from indexify import IndexifyClient
from unittest.mock import Mock, patch

@pytest.fixture
async def async_client():
    async with AsyncClient(app = app, base_url = "http://test") as client:
        yield client

@pytest.fixture
def mock_indexify_client():
    with patch("main.get_indexify_client") as mock:
        client = Mock(spec = IndexifyClient)
        mock.return_value.__aenter__.return_value = client
        yield client

# Unit Tests
@pytest.mark.asyncio
async def test_health_check(async_client):
    response = await async_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

@pytest.mark.asyncio
async def test_extract_content_success(async_client, mock_indexify_client):
    # Mock successful extraction
    mock_job = Mock()
    mock_job.wait_for_completion.return_value = [{"title": "Test Title"}]
    mock_indexify_client.submit_extraction_job.return_value = mock_job

    response = await async_client.post(
        "/extract",
        json={
            "url": "http://example.com",
            "schema": {
                "type": "object",
                "properties": {"title": {"type": "string"}},
                "required": ["title"]
            }
        }
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["data"]["title"] == "Test Title"

@pytest.mark.asyncio
async def test_extract_content_failure(async_client, mock_indexify_client):
    # Mock failed extraction
    mock_job = Mock()
    mock_job.wait_for_completion.return_value = [None]
    mock_indexify_client.submit_extraction_job.return_value = mock_job

    response = await async_client.post(
        "/extract",
        json={
            "url": "http://example.com",
            "schema": {
                "type": "object",
                "properties": {"title": {"type": "string"}},
                "required": ["title"]
            }
        }
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "error"