from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from ..models.user import UserIn, UserOut
from ..core.auth import authenticate_user, create_access_token, get_password_hash, ACCESS_TOKEN_EXPIRE_MINUTES
from ..core.database import users_collection

router = APIRouter()

@router.post("/register", response_model=UserOut)
async def register(user: UserIn):
    existing = await users_collection.find_one({"email": user.email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Użytkownik o podanym adresie email już istnieje"
        )
    
    hashed_password = get_password_hash(user.password)
    user_data = {
        "email": user.email, 
        "password": hashed_password
    }
    
    await users_collection.insert_one(user_data)
    return {"email": user.email}

@router.post("/login")
async def login(user: UserIn):  
    authenticated_user = await authenticate_user(user.email, user.password)  # Używamy email zamiast username
    if not authenticated_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy email lub hasło",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": authenticated_user["email"]}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}