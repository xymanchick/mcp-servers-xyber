"""
Tests for REST API endpoints.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from mcp_server_lurky.app import create_app
from mcp_server_lurky.lurky.models import SearchResponse, Discussion, SpaceDetails


class TestHealthEndpoint:
    """Test cases for health check endpoint."""

    def test_health_endpoint_returns_200(self, client: TestClient):
        """Test that health endpoint returns 200 OK."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_health_endpoint_response_structure(self, client: TestClient):
        """Test health endpoint response structure."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data
        assert "version" in data
        assert data["status"] == "ok"
        assert data["version"] == "0.1.0"


class TestSearchEndpoint:
    """Test cases for search endpoint."""

    def test_search_endpoint_success(
        self, app: FastAPI, mock_lurky_client: Mock, sample_search_response: SearchResponse
    ):
        """Test successful search request."""
        from mcp_server_lurky.dependencies import get_lurky_client
        
        mock_lurky_client.search_discussions = AsyncMock(return_value=sample_search_response)
        
        async def override_get_lurky_client():
            yield mock_lurky_client
        
        app.dependency_overrides[get_lurky_client] = override_get_lurky_client
        
        client = TestClient(app)
        try:
            response = client.get(
                "/hybrid/search?q=test&limit=10&page=0"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert len(data["discussions"]) == 1
            assert data["page"] == 0
            assert data["limit"] == 10
        finally:
            app.dependency_overrides.clear()

    def test_search_endpoint_empty_results(self, app: FastAPI, mock_lurky_client: Mock):
        """Test search endpoint with no results."""
        from mcp_server_lurky.dependencies import get_lurky_client
        
        empty_response = SearchResponse(discussions=[], total=0, page=0, limit=10)
        mock_lurky_client.search_discussions = AsyncMock(return_value=empty_response)
        
        async def override_get_lurky_client():
            yield mock_lurky_client
        
        app.dependency_overrides[get_lurky_client] = override_get_lurky_client
        
        client = TestClient(app)
        try:
            response = client.get(
                "/hybrid/search?q=nonexistent&limit=10&page=0"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            assert len(data["discussions"]) == 0
        finally:
            app.dependency_overrides.clear()

    def test_search_endpoint_missing_query(self, client: TestClient):
        """Test search endpoint with missing query parameter."""
        response = client.get("/hybrid/search")
        
        assert response.status_code == 422  # Validation error


class TestGetSpaceDetailsEndpoint:
    """Test cases for get space details endpoint."""

    def test_get_space_details_success(
        self, app: FastAPI, mock_lurky_client: Mock, sample_space_details: SpaceDetails
    ):
        """Test successful get space details request."""
        from mcp_server_lurky.dependencies import get_lurky_client, get_db
        
        mock_lurky_client.get_space_details = AsyncMock(return_value=sample_space_details)
        mock_lurky_client.get_space_discussions = AsyncMock(return_value=[])
        
        async def override_get_lurky_client():
            yield mock_lurky_client
        
        app.dependency_overrides[get_lurky_client] = override_get_lurky_client
        
        # Mock database to return None (cache miss)
        mock_db = Mock()
        mock_db.get_space = Mock(return_value=None)
        mock_db.save_space = Mock(return_value=True)
        app.dependency_overrides[get_db] = lambda: mock_db
        
        client = TestClient(app)
        try:
            response = client.get("/hybrid/spaces/test_space_id")
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "test_space_id"
            assert data["title"] == "Test Space Title"
        finally:
            app.dependency_overrides.clear()

    def test_get_space_details_not_found(self, app: FastAPI, mock_lurky_client: Mock):
        """Test get space details when space not found."""
        from mcp_server_lurky.dependencies import get_lurky_client, get_db
        from mcp_server_lurky.lurky.errors import LurkyNotFoundError
        
        mock_lurky_client.get_space_details = AsyncMock(side_effect=LurkyNotFoundError("Space not found"))
        
        async def override_get_lurky_client():
            yield mock_lurky_client
        
        app.dependency_overrides[get_lurky_client] = override_get_lurky_client
        
        mock_db = Mock()
        mock_db.get_space = Mock(return_value=None)
        app.dependency_overrides[get_db] = lambda: mock_db
        
        client = TestClient(app)
        try:
            response = client.get("/hybrid/spaces/nonexistent_space_id")
            
            assert response.status_code == 404
        finally:
            app.dependency_overrides.clear()


class TestLatestSummariesEndpoint:
    """Test cases for latest summaries endpoint."""

    def test_latest_summaries_success(
        self, app: FastAPI, mock_lurky_client: Mock, sample_space_details: SpaceDetails, sample_search_response: SearchResponse
    ):
        """Test successful latest summaries request."""
        from mcp_server_lurky.dependencies import get_lurky_client, get_db
        
        # Mock search to return discussions
        mock_lurky_client.search_discussions = AsyncMock(return_value=sample_search_response)
        mock_lurky_client.get_space_details = AsyncMock(return_value=sample_space_details)
        mock_lurky_client.get_space_discussions = AsyncMock(return_value=[])
        
        async def override_get_lurky_client():
            yield mock_lurky_client
        
        app.dependency_overrides[get_lurky_client] = override_get_lurky_client
        
        mock_db = Mock()
        mock_db.get_space = Mock(return_value=None)
        mock_db.save_space = Mock(return_value=True)
        app.dependency_overrides[get_db] = lambda: mock_db
        
        client = TestClient(app)
        try:
            response = client.get("/hybrid/latest-summaries?topic=test&count=1")
            
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) > 0
        finally:
            app.dependency_overrides.clear()

    def test_latest_summaries_missing_topic(self, client: TestClient):
        """Test latest summaries endpoint without topic parameter."""
        response = client.get("/hybrid/latest-summaries")
        
        assert response.status_code == 422  # Validation error
