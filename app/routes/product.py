from datetime import datetime
import os
import shutil
import uuid
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from ..core.auth import get_current_user
from ..core.database import users_collection

router = APIRouter(prefix="/product", tags=["product"])
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/analyze")
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
            
        # Here in the future, the image will be processed with OCR
        # and the text will be analyzed to extract ingredients and other information.
        
        # Mocked result
        mock_result = {
            "ingredients": [
                {"name": "Aqua", "description": "Woda", "risk_level": "low"},
                {"name": "Glycerin", "description": "Gliceryna (Nawilżenie)", "risk_level": "low"},
                {"name": "Sodium Laureth Sulfate", "description": "Surfaktant", "risk_level": "medium"},
                {"name": "Parfum", "description": "Substancja zapachowa", "risk_level": "high"}
            ],
            "compatibility_score": 0.75,
            "recommendation": "Ten kosmetyk może być odpowiedni dla Twojego typu skóry.",
            "file_saved": file_path
        }
        
        return mock_result
        
    except Exception as e:
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
            
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Wystąpił błąd podczas przetwarzania pliku: {str(e)}"
        )