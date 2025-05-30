from datetime import datetime
import os
import shutil
import uuid
import pytesseract
import numpy as np
import cv2
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from ..core.auth import get_current_user
from ..core.database import users_collection
from ..service.ingredients_cleaner import IngredientsCleaner

router = APIRouter(prefix="/product", tags=["product"])
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ingredientsCleaner = IngredientsCleaner()

@router.post("/extract-text")
async def analyze_product_image(
    image: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Analyzes a product image and returns the analysis result.
    """
    if not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Nieprawidłowy format pliku. Akceptowane są tylko obrazy."
        )
    try:
        file_extension = image.filename.split(".")[-1] if "." in image.filename else "jpg"
        unique_filename = f"{uuid.uuid4()}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
            
        print(f"Plik zapisany: {file_path}")
            
        img = cv2.imread(file_path)
        
        # PROBABLY UNNECESSARY
        # gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)    # grayscale conversion
        # gray = cv2.GaussianBlur(gray, (5, 5), 0)        # Gaussian blur to reduce noise
        # thresh = cv2.adaptiveThreshold(                 # Binary thresholding
        #     gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        #     cv2.THRESH_BINARY, 11, 2
        # )
        
        
        extracted_text = pytesseract.image_to_string(img, lang='eng+pol')
        print(f"Rozpoznany tekst: {extracted_text}")
        
        ingredients = ingredientsCleaner.extract_ingredients_from_text(extracted_text)
        
        return {
            "raw_text": extracted_text,
            "extracted_ingredients": ingredients,
            "file_id": unique_filename,
        }
        
       
    except Exception as e:
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
            
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Wystąpił błąd podczas przetwarzania pliku: {str(e)}"
        )
        
@router.post("/analyze-ingredients")
async def analyze_ingredients(
    ingredients_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """Analyzes confirmed ingredients against user profile.

    Args:
        ingredients_data (dict): _description_
        current_user (dict, optional): _description_. Defaults to Depends(get_current_user).
    """
    confirmed_ingredients = ingredients_data.get("confirmed_ingredients", [])
    if not confirmed_ingredients:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Brak potwierdzonych składników do analizy."
        )
    user_profile = await users_collection.find_one({"email": current_user["email"]})
    
    analyzed_ingredients = []
    
    # MOCK
    recommendation = "Ten produkt może być odpowiedni dla Twojego typu skóry."
    if any(item["risk_level"] == "high" for item in analyzed_ingredients):
        recommendation = "Ten produkt zawiera składniki, które mogą nie być odpowiednie dla Twojej skóry."
    compatibility_score = 0
    
    return {
        "ingredients": analyzed_ingredients,
        "compatibility_score": compatibility_score,
        "recommendation": recommendation
    }