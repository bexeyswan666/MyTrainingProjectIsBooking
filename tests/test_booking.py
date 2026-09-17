from fastapi.testclient import TestClient

from main import app
from depencies import create_token
from datetime import timedelta

client = TestClient(app)

def test_hotels_room_id_good():
    response = client.get("/hotels/rooms/2",headers={"X-token":"coneofsilence"})
    assert response.status_code == 200
    assert response.json() == {
        "id": 2,
        "hotel_id": 1,
        "name": "Standard",
        "price": 4500,
        "count_people": 3
    }
def test_hotels_room_id_bad():
    response = client.get("/hotels/rooms/123",headers={"X-token":"coneofsilence"})
    assert response.status_code == 404
    assert response.json() == {
  "detail": "Not found"
}

def test_booking_create_good():
    token = create_token({"sub":"admin"},timedelta(minutes=30))
    response = client.post("/booking/2",params={"date_to":"2026-12-21",
                                                "date_from":"2026-12-20"},
                                                headers={"Authorization":f"Bearer {token}"})
    assert response.status_code == 201
    assert response.json() == {
  "status": "create booking!"
    }

def test_booking_create_bad():
    token = create_token({"sub":"admin"},timedelta(minutes=30))
    response = client.post("/booking/2",params={"date_to":"2026-12-15",
                                                "date_from":"2026-12-19"},
                                                headers={"Authorization":f"Bearer {token}"})
    assert response.status_code == 400
    assert response.json() == {
  "detail": "date_to must be after date_from"
    }

    