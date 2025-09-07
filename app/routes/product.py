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
from ..service.chemical_identity_mapper import ChemicalIdentityMapper
from ..prettier import save_analysis_results


router = APIRouter(prefix="/product", tags=["product"])
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ingredientsCleaner = IngredientsCleaner()
chemical_mapper = ChemicalIdentityMapper()

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
        print(f" text: {extracted_text}")
        
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
        
@router.post("/analyze-ingredients")  ## Not used right now
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
    
@router.post("/map-chemical-identities")
async def map_chemical_identities(
    ingredients_data: dict,
    current_user: dict = Depends(get_current_user)
):
    """
    Map INCI ingredients to comprehensive chemical data from all sources.
    
    Args:
        ingredients_data: {"ingredients": ["aqua", "glycerin", ...]}
    """
    ingredients = ingredients_data.get("ingredients", [])
    if not ingredients:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Brak składników do mapowania."
        )
    
    print(f"Start mapping results")
    mapping_results = await chemical_mapper.map_ingredients_batch(ingredients)
    
    successful_mappings = [r for r in mapping_results if r.found]
    failed_mappings = [r for r in mapping_results if not r.found]
    
    total_domains_available = 0
    domains_with_data = 0
    
    for result in successful_mappings:
        if result.comprehensive_data:
            total_domains_available += 4  # 4 possible domains
            if result.comprehensive_data.basic_identifiers:
                domains_with_data += 1
            if result.comprehensive_data.toxicology:
                domains_with_data += 1
            if result.comprehensive_data.regulatory:
                domains_with_data += 1
            if result.comprehensive_data.physical_chemical:
                domains_with_data += 1
    
    data_coverage = (domains_with_data / total_domains_available * 100) if total_domains_available > 0 else 0
    
    info = {
        "total_ingredients": len(ingredients),
        "successful_mappings": len(successful_mappings),
        "failed_mappings": len(failed_mappings),
        "results": [r.dict() for r in mapping_results],
        "comprehensive_summary": {
            "success_rate": len(successful_mappings) / len(ingredients) * 100,
            "data_coverage_percentage": data_coverage,
            "avg_processing_time_ms": sum(r.processing_time_ms for r in mapping_results) / len(mapping_results),
            "sources_used": list(set(source for r in mapping_results 
                                   if r.comprehensive_data 
                                   for source in r.comprehensive_data.sources_used)),
            "domains_summary": {
                "basic_identifiers": sum(1 for r in mapping_results if r.comprehensive_data and r.comprehensive_data.basic_identifiers),
                "toxicology": sum(1 for r in mapping_results if r.comprehensive_data and r.comprehensive_data.toxicology),
                "regulatory": sum(1 for r in mapping_results if r.comprehensive_data and r.comprehensive_data.regulatory),
                "physical_chemical": sum(1 for r in mapping_results if r.comprehensive_data and r.comprehensive_data.physical_chemical)
            }
        }
    }

    save_analysis_results(info)

    print(f"Mapping results: {info}")
    return info
