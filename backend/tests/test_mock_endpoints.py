import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from main import app
from middleware.auth_middleware import verify_token
from models.project import ProjectCreate, ProjectStatusEnum
from models.user import GoogleOAuthData, UserInDB
from services.auth_service import AuthService
from services.project_service import get_project_service
from services.user_service import get_user_service

client = TestClient(app)

# Initialize services for testing
auth_service = AuthService()
project_service = get_project_service()
user_service = get_user_service()


def mock_verify_token():
    """Mock verify_token that returns test user UUID as string"""
    return "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def sample_user():
    """Sample user for testing - uses UUID that matches our mock project ownership"""
    test_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    return UserInDB(
        id=test_user_id,
        email="test@example.com",
        name="Test User",
        avatar_url="https://example.com/avatar.jpg",
        google_id="google_123",
        is_active=True,
        is_verified=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def test_access_token(sample_user):
    """Create a valid access token for testing"""
    return auth_service.create_access_token(str(sample_user.id), sample_user.email)


@pytest.fixture
def test_user_in_db(sample_user):
    """Ensure test user exists in database"""
    try:
        # Try to create user in database (if not exists)
        user_service.create_user_from_google(
            google_data=GoogleOAuthData(
                google_id=sample_user.google_id,
                email=sample_user.email,
                name=sample_user.name,
                avatar_url=sample_user.avatar_url,
            )
        )
    except Exception:
        # User might already exist, that's fine
        pass
    return sample_user


@pytest.fixture
def test_project_in_db(test_user_in_db):
    """Create a test project in database"""
    project_data = ProjectCreate(
        name="Sales Data Analysis", description="Test project for sales analysis"
    )
    try:
        project = project_service.create_project(project_data, test_user_in_db.id)
        # Update project to have a known ID for testing
        return project
    except Exception:
        # Project might already exist
        projects = project_service.get_projects_by_user(test_user_in_db.id, limit=1)
        if projects:
            return projects[0]
        raise


def test_google_login(test_client, sample_user):
    """Test Google OAuth login endpoint with development mode"""
    mock_access_token = "mock_access_token"
    mock_refresh_token = "mock_refresh_token"

    with patch(
        "api.auth.auth_service.login_with_google",
        return_value=(sample_user, mock_access_token, mock_refresh_token, False),
    ):
        response = test_client.post(
            "/auth/google", json={"google_token": "mock_google_token_123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert "user" in data["data"]
        assert data["data"]["user"]["email"] == "test@example.com"


def test_get_current_user(test_client, sample_user, test_access_token):
    """Test get current user endpoint"""
    with patch(
        "api.auth.auth_service.get_current_user",
        return_value=sample_user,
    ):
        response = test_client.get(
            "/auth/me", headers={"Authorization": f"Bearer {test_access_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["email"] == "test@example.com"


def test_get_projects(
    test_client, test_access_token, test_user_in_db, test_project_in_db
):
    """Test get projects endpoint"""
    app.dependency_overrides[verify_token] = mock_verify_token
    try:
        response = test_client.get(
            "/projects?page=1&limit=10",
            headers={"Authorization": f"Bearer {test_access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "items" in data["data"]
        assert "total" in data["data"]
        assert len(data["data"]["items"]) >= 1  # Should have at least our test project
    finally:
        app.dependency_overrides.clear()


def test_create_project(test_client, test_access_token, test_user_in_db):
    """Test create project endpoint"""
    app.dependency_overrides[verify_token] = mock_verify_token
    try:
        response = test_client.post(
            "/projects",
            json={"name": "Test Project", "description": "Test description"},
            headers={"Authorization": f"Bearer {test_access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["project"]["name"] == "Test Project"
        assert "upload_url" in data["data"]
    finally:
        app.dependency_overrides.clear()


def test_get_project(
    test_client, test_access_token, test_user_in_db, test_project_in_db
):
    """Test get single project endpoint"""
    app.dependency_overrides[verify_token] = mock_verify_token
    try:
        response = test_client.get(
            f"/projects/{test_project_in_db.id}",
            headers={"Authorization": f"Bearer {test_access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == str(test_project_in_db.id)
        assert data["data"]["name"] == "Sales Data Analysis"
    finally:
        app.dependency_overrides.clear()


def test_csv_preview(
    test_client, test_access_token, test_user_in_db, test_project_in_db
):
    """Test CSV preview endpoint"""
    app.dependency_overrides[verify_token] = mock_verify_token
    try:
        response = test_client.get(
            f"/chat/{test_project_in_db.id}/preview",
            headers={"Authorization": f"Bearer {test_access_token}"},
        )
        # The preview endpoint returns 404 for projects without CSV data
        # This is expected behavior for new projects
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "CSV preview not available"
    finally:
        app.dependency_overrides.clear()


def test_send_message(
    test_client, test_access_token, test_user_in_db, test_project_in_db
):
    """Test send chat message endpoint"""
    app.dependency_overrides[verify_token] = mock_verify_token
    try:
        response = test_client.post(
            f"/chat/{test_project_in_db.id}/message",
            json={"message": "Show me total sales by product"},
            headers={"Authorization": f"Bearer {test_access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message" in data["data"]
        assert "result" in data["data"]
        assert data["data"]["result"]["result_type"] in ["table", "chart", "summary"]
    finally:
        app.dependency_overrides.clear()


def test_query_suggestions(
    test_client, test_access_token, test_user_in_db, test_project_in_db
):
    """Test query suggestions endpoint"""
    app.dependency_overrides[verify_token] = mock_verify_token
    try:
        response = test_client.get(
            f"/chat/{test_project_in_db.id}/suggestions",
            headers={"Authorization": f"Bearer {test_access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) > 0
        assert all("text" in suggestion for suggestion in data["data"])
    finally:
        app.dependency_overrides.clear()


def test_unauthorized_access(test_client):
    """Test that endpoints require authentication"""
    response = test_client.get("/projects")
    assert response.status_code == 401


def test_invalid_token(test_client):
    """Test invalid token handling"""
    response = test_client.get(
        "/projects", headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401


def test_logout(test_client, sample_user, test_access_token):
    """Test logout endpoint"""
    with patch(
        "api.auth.auth_service.get_current_user",
        return_value=sample_user,
    ):
        response = test_client.post(
            "/auth/logout", headers={"Authorization": f"Bearer {test_access_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["message"] == "Logged out successfully"


def test_refresh_token(test_client, sample_user):
    """Test refresh token endpoint"""
    mock_refresh_token = "mock_refresh_token"
    mock_new_access_token = "new_access_token"
    with patch(
        "api.auth.auth_service.refresh_access_token",
        return_value=(mock_new_access_token, sample_user),
    ):
        response = test_client.post(
            "/auth/refresh", json={"refresh_token": mock_refresh_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]


def test_project_status(
    test_client, test_access_token, test_user_in_db, test_project_in_db
):
    """Test project status endpoint"""
    app.dependency_overrides[verify_token] = mock_verify_token
    try:
        response = test_client.get(
            f"/projects/{test_project_in_db.id}/status",
            headers={"Authorization": f"Bearer {test_access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "status" in data["data"]
        assert "progress" in data["data"]
    finally:
        app.dependency_overrides.clear()


def test_get_upload_url(
    test_client, test_access_token, test_user_in_db, test_project_in_db
):
    """Test get upload URL endpoint"""
    app.dependency_overrides[verify_token] = mock_verify_token
    try:
        response = test_client.get(
            f"/projects/{test_project_in_db.id}/upload-url",
            headers={"Authorization": f"Bearer {test_access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "upload_url" in data["data"]
        assert "upload_fields" in data["data"]
    finally:
        app.dependency_overrides.clear()


def test_get_messages(
    test_client, test_access_token, test_user_in_db, test_project_in_db
):
    """Test get chat messages endpoint"""
    app.dependency_overrides[verify_token] = mock_verify_token
    try:
        response = test_client.get(
            f"/chat/{test_project_in_db.id}/messages",
            headers={"Authorization": f"Bearer {test_access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "items" in data["data"]
        assert len(data["data"]["items"]) >= 0
    finally:
        app.dependency_overrides.clear()


def test_invalid_google_token(test_client):
    """Test invalid Google token"""
    with patch(
        "api.auth.auth_service.verify_google_token",
        side_effect=ValueError("Invalid Token"),
    ):
        response = test_client.post(
            "/auth/google", json={"google_token": "invalid_token"}
        )
        assert response.status_code == 401


def test_project_not_found(test_client, test_access_token, test_user_in_db):
    """Test project not found error"""
    app.dependency_overrides[verify_token] = mock_verify_token
    try:
        # Use a valid UUID that doesn't exist
        nonexistent_uuid = "00000000-0000-0000-0000-000000000999"
        response = test_client.get(
            f"/projects/{nonexistent_uuid}",
            headers={"Authorization": f"Bearer {test_access_token}"},
        )
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_chart_query_response(
    test_client, test_access_token, test_user_in_db, test_project_in_db
):
    """Test chart query response type"""
    app.dependency_overrides[verify_token] = mock_verify_token
    try:
        response = test_client.post(
            f"/chat/{test_project_in_db.id}/message",
            json={"message": "show me a chart"},
            headers={"Authorization": f"Bearer {test_access_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["result"]["result_type"] == "chart"
        assert "chart_config" in data["data"]["result"]
    finally:
        app.dependency_overrides.clear()
