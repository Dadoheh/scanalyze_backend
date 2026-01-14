from datetime import datetime
import os
import shutil
import uuid
import pytesseract
import numpy as np
import cv2
from typing import List
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.service.decision_service import decide_product
from app.service.neo4j_sync_service import upsert_ingredient_from_identity, upsert_product, upsert_user_profile, upsert_ingredient_with_hed
from app.service.hed_integration_service import HEDIntegrationService
from ..core.auth import get_current_user
from ..core.database import users_collection
from ..core.neo4j_client import neo4j_client
from ..service.ingredients_cleaner import IngredientsCleaner
from ..service.chemical_identity_mapper import ChemicalIdentityMapper
from ..prettier import save_analysis_results
import logging

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/product", tags=["product"])
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ingredientsCleaner = IngredientsCleaner()
chemical_mapper = ChemicalIdentityMapper()


class AnalyzeIngredientsRequest(BaseModel):
    """Request model for ingredient analysis."""
    ingredients: List[str]
    store_in_neo4j: bool = True


class HEDCalculationSummary(BaseModel):
    """Summary of HED calculation for one ingredient."""
    inci_name: str
    hed_calculated: bool
    hed_mg_kg: float = None
    safe_concentration_percent: float = None
    risk_assessment: str = None
    recommendation: str = None
    source_toxicity_type: str = None
    source_animal_species: str = None


class IngredientAnalysisResponse(BaseModel):
    """Response with complete analysis results."""
    total_ingredients: int
    successful_mappings: int
    failed_mappings: int
    hed_calculations_completed: int
    stored_in_neo4j: bool
    hed_summaries: List[HEDCalculationSummary]

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
    Map INCI ingredients to comprehensive chemical data from all sources WITH HED calculations.
    
    This endpoint now:
    1. Maps ingredients to PubChem + ToxVal data
    2. Calculates Human Equivalent Doses (HED) from animal toxicology
    3. Stores complete data (identifiers + HED) in Neo4j
    4. Returns product safety decision
    
    Args:
        ingredients_data: {"ingredients": ["aqua", "glycerin", ...]}
    """
    ingredients = ingredients_data.get("ingredients", [])
    if not ingredients:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Brak składników do mapowania."
        )
    
    logger.info(f"Mapping {len(ingredients)} ingredients with HED calculations")
    mapping_results = await chemical_mapper.map_ingredients_batch(ingredients)
    
    user_profile = await users_collection.find_one({"email": current_user["email"]})
    user_weight_kg = user_profile.get("weight", 60.0) if user_profile else 60.0
    
    hed_service = HEDIntegrationService(human_weight_kg=user_weight_kg)
    logger.info(f"Using user weight: {user_weight_kg} kg for HED calculations")
    
    ing_keys = []
    hed_summaries = []
    hed_calculated_count = 0
    
    for r in mapping_results:
        try:
            # Calculate HED if toxicology data is available
            neo4j_hed_data = None
            if r.found and r.comprehensive_data and r.comprehensive_data.toxicology:
                try:
                    hed_result = hed_service.process_ingredient_comprehensive_data(
                        r.comprehensive_data.dict()
                    )
                    neo4j_hed_data = hed_result.get("neo4j_data")
                    
                    if hed_result.get("hed_calculated"):
                        hed_calculated_count += 1
                        logger.info(f"✓ HED calculated for {r.inci_name}: {neo4j_hed_data.get('safe_concentration_percent')}%")
                        
                        # Add to summaries
                        hed_summaries.append({
                            "inci_name": r.inci_name,
                            "hed_calculated": True,
                            "hed_mg_kg": neo4j_hed_data.get("hed_mg_kg"),
                            "safe_concentration_percent": neo4j_hed_data.get("safe_concentration_percent"),
                            "risk_assessment": neo4j_hed_data.get("risk_assessment"),
                            "recommendation": neo4j_hed_data.get("recommendation"),
                        })
                    else:
                        logger.info(f"○ HED not calculated for {r.inci_name}: {hed_result.get('reason')}")
                        hed_summaries.append({
                            "inci_name": r.inci_name,
                            "hed_calculated": False,
                            "reason": hed_result.get("reason"),
                        })
                except Exception as hed_err:
                    logger.warning(f"HED calculation error for {r.inci_name}: {hed_err}")
                    hed_summaries.append({
                        "inci_name": r.inci_name,
                        "hed_calculated": False,
                        "reason": str(hed_err),
                    })
            
            # Upsert to Neo4j with HED data (if available)
            await upsert_ingredient_with_hed(r, neo4j_hed_data)
            
            # Generate ingredient key
            cd = r.comprehensive_data
            key = (cd.basic_identifiers.inchi_key.lower() if cd and cd.basic_identifiers and cd.basic_identifiers.inchi_key
                   else f"cas:{cd.basic_identifiers.cas_number}" if cd and cd.basic_identifiers and cd.basic_identifiers.cas_number
                   else f"dtxsid:{cd.toxicology.dtxsid}" if cd and cd.toxicology and cd.toxicology.dtxsid
                   else f"inci:{r.inci_name.lower()}")
            
            # For unmapped ingredients, create basic Ingredient node with inci name
            if not r.found or not cd:
                await neo4j_client.run("""
                MERGE (i:Ingredient {key: $key})
                SET i.inci = $inci_name
                """, {"key": key, "inci_name": r.inci_name})
            
            ing_keys.append(key)
        except Exception as e:
            logger.error(f"Failed to process {r.inci_name}: {e}")

    product_id = f"tmp-{uuid.uuid4()}"
    await upsert_product(product_id, ing_keys)

    # Send full user profile to Neo4j for decision engine
    user_profile = await users_collection.find_one({"email": current_user["email"]})
    
    # Legacy conditions mapping (for backward compatibility with Condition nodes)
    conditions = []
    if user_profile:
        if user_profile.get("sensitiveSkin"): conditions.append("sensitive_skin")
        if user_profile.get("hasAllergies"): conditions.append("allergies")
        if user_profile.get("acneVulgaris"): conditions.append("acne_vulgaris")
        if user_profile.get("psoriasis"): conditions.append("psoriasis")
        if user_profile.get("eczema"): conditions.append("eczema")
        if user_profile.get("rosacea"): conditions.append("rosacea")
    
    # Upsert full profile to Neo4j (for advanced decision engine)
    await upsert_user_profile(
        current_user["email"], 
        conditions=conditions,
        profile_data=user_profile
    )

    decision = await decide_product(current_user["email"], product_id, preferred_routes=["dermal"])

    # Calculate data coverage - prettier for testing
    info = _create_info(mapping_results, ingredients)
    
    # Add HED summary to info
    info["hed_summary"] = {
        "total_ingredients": len(ingredients),
        "hed_calculated": hed_calculated_count,
        "hed_failed": len(ingredients) - hed_calculated_count,
        "hed_details": hed_summaries,
    }
    
    # TODO - save only in debug mode
    save_analysis_results(info)
    save_analysis_results(decision, prefix="decision_result")  # Save decision separately for debugging

    logger.info(f"Mapping complete: {len(mapping_results)} ingredients, {hed_calculated_count} with HED")
    return {"mapping": info, "decision": decision}


@router.get("/ingredient/{inci_name}/hed")
async def get_ingredient_hed(inci_name: str):
    """
    Get HED calculation for a single ingredient.
    
    Args:
        inci_name: INCI name of the ingredient
    
    Returns:
        HED calculation results with safety assessment
    """
    logger.info(f"Getting HED for ingredient: {inci_name}")
    
    hed_service = HEDIntegrationService()
    
    # Get comprehensive data
    result = await chemical_mapper.map_ingredient(inci_name)
    
    if not result.found:
        raise HTTPException(status_code=404, detail=f"No data found for {inci_name}")
    
    # Calculate HED
    hed_result = hed_service.process_ingredient_comprehensive_data(
        result.comprehensive_data.dict()
    )
    
    return {
        "inci_name": inci_name,
        "comprehensive_data": result.comprehensive_data.dict(),
        "hed_analysis": hed_result,
    }


@router.get("/debug/neo4j/{inci_name}")
async def debug_neo4j_ingredient(inci_name: str):
    """
    Debug endpoint - shows what's stored in Neo4j for an ingredient.
    
    Returns complete Neo4j data including:
    - Ingredient node properties
    - Hazard nodes and relationships
    - HEDAssessment node (if exists)
    - Effects linked to hazards
    """
    from app.core.neo4j_client import neo4j_client
    
    # Query all data for ingredient
    result = await neo4j_client.run("""
    MATCH (i:Ingredient)
    WHERE i.inci = $inci OR i.key CONTAINS $inci
    
    // Get basic ingredient data
    WITH i
    OPTIONAL MATCH (i)-[:HAS_HAZARD]->(h:Hazard)
    OPTIONAL MATCH (h)-[:CAUSES]->(e:Effect)
    OPTIONAL MATCH (i)-[:HAS_HED_ASSESSMENT]->(hed:HEDAssessment)
    
    RETURN i AS ingredient,
           collect(DISTINCT h) AS hazards,
           collect(DISTINCT e) AS effects,
           collect(DISTINCT hed) AS hed_assessments
    """, {"inci": inci_name.lower()})
    
    records = [r async for r in result]
    
    if not records:
        raise HTTPException(status_code=404, detail=f"No Neo4j data found for {inci_name}")
    
    record = records[0]
    
    return {
        "inci_name": inci_name,
        "ingredient": dict(record["ingredient"]) if record["ingredient"] else None,
        "hazards": [dict(h) for h in record["hazards"] if h],
        "effects": [dict(e) for e in record["effects"] if e],
        "hed_assessments": [dict(hed) for hed in record["hed_assessments"] if hed],
        "has_hed_calculation": len([hed for hed in record["hed_assessments"] if hed]) > 0,
    }


@router.get("/debug/neo4j_stats")
async def debug_neo4j_stats():
    """
    Get Neo4j database statistics - how many nodes of each type exist.
    """
    from app.core.neo4j_client import neo4j_client
    
    # Count nodes by type
    result = await neo4j_client.run("""
    CALL db.labels() YIELD label
    CALL apoc.cypher.run('MATCH (n:`' + label + '`) RETURN count(n) as count', {})
    YIELD value
    RETURN label, value.count AS count
    ORDER BY value.count DESC
    """, {})
    
    stats = []
    async for record in result:
        stats.append({
            "node_type": record["label"],
            "count": record["count"]
        })
    
    # Get HED assessments summary
    hed_result = await neo4j_client.run("""
    MATCH (h:HEDAssessment)
    RETURN count(h) AS total_hed_assessments,
           avg(h.hed_mg_kg) AS avg_hed_mg_kg,
           avg(h.safe_concentration_percent) AS avg_safe_concentration_percent,
           collect(DISTINCT h.risk_assessment) AS risk_assessments
    """, {})
    
    hed_stats = None
    async for record in hed_result:
        hed_stats = dict(record)
    
    return {
        "node_counts": stats,
        "hed_summary": hed_stats,
    }


def _create_info(mapping_results, ingredients):
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
    return info
