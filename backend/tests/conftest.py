import os

import pytest
from fastapi.testclient import TestClient

# Set environment variables for testing BEFORE importing the application
os.environ["DATABASE_URL"] = "sqlite:///test.db"  # Use file-based SQLite for tests
os.environ["JWT_SECRET"] = "test_secret"
os.environ["TESTING"] = "true"

# Now that the environment is configured, we can import the application
from main import app
from models.base import Base
from models.project import ProjectTable  # Import to register with Base
from models.user import UserTable  # Import to register with Base
from services.database_service import get_db_service
from services.project_service import (  # Ensure ProjectService is imported
    get_project_service,
)
from services.user_service import get_user_service  # Ensure UserService is imported


@pytest.fixture(scope="session", autouse=True)
def test_db_setup():
    """
    Fixture to create and tear down the test database.
    This runs once per test session.
    """
    # Force the database service to use the test URL
    db_service = get_db_service()
    db_service.reconnect()

    # Ensure all services are imported to register models
    _ = get_user_service()
    _ = get_project_service()

    # Create tables
    Base.metadata.create_all(bind=db_service.engine)

    yield

    # Drop tables
    Base.metadata.drop_all(bind=db_service.engine)


@pytest.fixture(scope="function")
def test_client(test_db_setup):
    """
    A TestClient that uses the in-memory SQLite database.
    Each test function gets a clean database.
    """
    # Ensure tables are created for each test
    db_service = get_db_service()
    Base.metadata.drop_all(bind=db_service.engine)  # Clean slate
    Base.metadata.create_all(bind=db_service.engine)  # Recreate tables

    with TestClient(app) as client:
        yield client
