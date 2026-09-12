from fastapi.testclient import TestClient

from app.main import APP_VERSION, app

client = TestClient(app)

def test_version_endpoint():
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json() == {"version": APP_VERSION}
