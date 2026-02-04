from fastapi.testclient import TestClient
from app.main import app
import pytest

client = TestClient(app)

def test_404_not_found():
    response = client.get("/non-existent-route")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert "code" in data
    assert data["code"] == "HTTP_ERROR"

def test_422_validation_error():
    # Sending invalid data types to an endpoint expecting specific types
    # Assuming serving captcha takes a string, let's try a route if we have one with body
    # or just rely on path params. 
    # Let's try to hit the captcha endpoint which is GET, but let's try a POST to it? No that's 405.
    # Let's try to hit an endpoint that requires args.
    # The captcha endpoint is /api/v1/captcha/{user_id}.
    # We don't have many POST endpoints exposed in main.py, mainly imports from api.aisensy
    pass 

def test_validation_error_structure():
    # We can define a temporary route to test validation
    from pydantic import BaseModel
    
    class Item(BaseModel):
        name: str
        price: int

    @app.post("/test-validation")
    def create_item(item: Item):
        return item

    response = client.post("/test-validation", json={"name": "foo", "price": "invalid"})
    assert response.status_code == 422
    data = response.json()
    assert data["code"] == "VALIDATION_ERROR"
    assert "details" in data
    assert len(data["details"]) > 0

def test_custom_exception():
    from app.core.exceptions import ResourceNotFoundError
    
    @app.get("/test-custom-error")
    def trigger_custom_error():
        raise ResourceNotFoundError(message="Item not found")

    response = client.get("/test-custom-error")
    assert response.status_code == 404
    data = response.json()
    assert data["code"] == "NOT_FOUND"
    assert data["error"] == "Item not found"
