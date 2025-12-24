import pytest
from fastapi.testclient import TestClient
from app.main import create_app


@pytest.fixture()
def client() -> TestClient:
    """
    Creates a fresh FastAPI app and TestClient for each test.
    This avoids shared state between tests.
    """
    app = create_app()
    return TestClient(app)
