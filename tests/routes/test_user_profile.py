import pytest
from fastapi.testclient import TestClient

from main import app
from app.core.auth import get_current_user

client = TestClient(app)

test_user = {
    "email": "test@example.com",
    "password": "hashedpassword"
}

@pytest.fixture
def mock_current_user():
    async def override_get_current_user():
        return test_user
    
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield
    app.dependency_overrides = {}

test_profile_data = {
    "age": 42,
    "gender": "Kobieta",
    "weight": 110,
    "height": 186,
    "skinType": None,
    "sensitiveSkin": False,
    "atopicSkin": None,
    "acneProne": None,
    "hasAllergies": None,
    "cosmeticAllergies": ["Barwniki"],
    "generalAllergies": [],
    "acneVulgaris": None,
    "psoriasis": None,
    "eczema": None,
    "rosacea": None,
    "photosensitizingDrugs": None,
    "diuretics": None,
    "otherMedications": None,
    "medicalProcedures": None,
    "smoking": "Okazjonalnie",
    "stressLevel": 6,
    "tanning": "Często",
    "pregnancy": None
}

@pytest.fixture
def mock_mongodb(monkeypatch):
    stored_profile = {}
    
    async def mock_update_one(query, update_data):
        email = query.get("email")
        if email == test_user["email"]:
            for key, value in update_data["$set"].items():
                stored_profile[key] = value
            return True
        return False
    
    async def mock_find_one(query):
        email = query.get("email")
        if email == test_user["email"]:
            return {**test_user, **stored_profile}
        return None
    
    from app.core.database import users_collection
    monkeypatch.setattr(users_collection, "update_one", mock_update_one)
    monkeypatch.setattr(users_collection, "find_one", mock_find_one)

def test_update_and_get_user_profile(mock_current_user, mock_mongodb):
    """Testuje aktualizację i pobieranie profilu użytkownika z wartościami null."""
    
    response = client.post("/user/profile", json=test_profile_data)
    assert response.status_code == 200
    
    profile_response = response.json()
    
    assert profile_response["age"] == 42
    assert profile_response["gender"] == "Kobieta"
    assert profile_response["weight"] == 110
    assert profile_response["height"] == 186
    
    assert profile_response["sensitiveSkin"] == False
    
    assert "Barwniki" in profile_response["cosmeticAllergies"]
    assert len(profile_response["generalAllergies"]) == 0
    
    assert profile_response["smoking"] == "Okazjonalnie"
    assert profile_response["stressLevel"] == 6
    assert profile_response["tanning"] == "Często"
    
    get_response = client.get("/user/profile")
    assert get_response.status_code == 200
    
    get_profile = get_response.json()
    assert get_profile["age"] == 42
    assert get_profile["gender"] == "Kobieta"
    assert get_profile["sensitiveSkin"] == False
    assert "Barwniki" in get_profile["cosmeticAllergies"]
    assert get_profile["smoking"] == "Okazjonalnie"
    assert len(get_profile) == 23
    