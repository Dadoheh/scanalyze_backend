from fastapi import APIRouter, Depends, HTTPException, status
from ..models.user import UserProfileIn, UserProfileOut
from ..core.auth import get_current_user
from ..core.database import users_collection

router = APIRouter()

@router.get("/profile", response_model=UserProfileOut)
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    user = await users_collection.find_one({"email": current_user["email"]})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Użytkownik nie znaleziony"
        )
    return user

@router.post("/profile", response_model=UserProfileOut)
async def update_user_profile(
    profile: UserProfileIn,
    current_user: dict = Depends(get_current_user)
):
    user = await users_collection.find_one({"email": current_user["email"]})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Użytkownik nie znaleziony"
        )
    
    profile_dict = profile.dict(exclude_none=True)
    
    # Aktualizacja dokumentu użytkownika
    await users_collection.update_one(
        {"email": current_user["email"]},
        {"$set": {**profile_dict}}
    )
    
    updated_user = await users_collection.find_one({"email": current_user["email"]})
    return updated_user