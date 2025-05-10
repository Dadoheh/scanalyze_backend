from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.models.user import UserIn, UserOut
from app.core.database import users_collection

router = APIRouter()

@router.post("/login")
async def login(user: UserIn):
    existing = await users_collection.find_one({"email": user.email})
    if not existing or existing["password"] != user.password:
        raise HTTPException(status_code=401, detail="Niepoprawne dane logowania")
    return {"access_token": "fake-jwt-token", "user": {"email": user.email}}

@router.post("/register")
async def register(user: UserIn):
    existing = await users_collection.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Użytkownik już istnieje")
    await users_collection.insert_one(user.dict())
    return {"message": "Zarejestrowano pomyślnie"}
