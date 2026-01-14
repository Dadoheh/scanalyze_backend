from typing import Any, Dict, List, Optional
from datetime import datetime
from app.core.neo4j_client import neo4j_client
from app.models.chemical_identity import ChemicalIdentityResult, ToxicologyData, BasicChemicalIdentifiers

def _ingredient_key(basic: Optional[BasicChemicalIdentifiers], tox: Optional[ToxicologyData], inci_name: str) -> str:
    if basic and basic.inchi_key:
        return basic.inchi_key.lower()
    if basic and basic.cas_number:
        return f"cas:{basic.cas_number}"
    if tox and tox.dtxsid:
        return f"dtxsid:{tox.dtxsid}"
    return f"inci:{inci_name.lower()}"

def _hazards_from_tox(tox: ToxicologyData) -> List[Dict[str, Any]]:
    hazards: List[Dict[str, Any]] = []
    # allergen_status → Effect: sensitization
    if tox.allergen_status:
        sev = "high" if "1a" in tox.allergen_status.lower() else ("medium" if "1b" in tox.allergen_status.lower() else "medium")
        hazards.append({
            "type": "allergen_status",
            "value": tox.allergen_status,
            "route": "dermal",
            "unit": "-",
            "species": "-",
            "effect": "sensitization",
            "severity": sev,
            "source": tox.source,
            "confidence": tox.confidence_score,
        })
    # irritation_potential → Effect: irritation
    if tox.irritation_potential:
        hazards.append({
            "type": "irritation",
            "value": tox.irritation_potential,
            "route": "dermal",
            "unit": "-",
            "species": "-",
            "effect": "irritation",
            "severity": "medium",
            "source": tox.source,
            "confidence": tox.confidence_score,
        })
    # sensitization_risk → Effect: sensitization
    if tox.sensitization_risk and not tox.allergen_status:
        hazards.append({
            "type": "sensitization_risk",
            "value": tox.sensitization_risk,
            "route": "dermal",
            "unit": "-",
            "species": "-",
            "effect": "sensitization",
            "severity": "medium",
            "source": tox.source,
            "confidence": tox.confidence_score,
        })
    # NOAEL
    if tox.noael_value is not None:
        hazards.append({
            "type": "NOAEL",
            "value": tox.noael_value,
            "route": "dermal",
            "unit": "mg/kg-day",
            "species": "-",
            "effect": "threshold",
            "severity": "low",
            "source": tox.source,
            "confidence": tox.confidence_score,
        })
    # DNEL/safe_concentration
    if tox.safe_concentration:
        hazards.append({
            "type": "DNEL",
            "value": tox.safe_concentration,
            "route": "dermal",
            "unit": "-",
            "species": "Human",
            "effect": "limit",
            "severity": "low",
            "source": tox.source,
            "confidence": tox.confidence_score,
        })
    # carcinogenicity
    if tox.carcinogenicity:
        hazards.append({
            "type": "carcinogenicity",
            "value": tox.carcinogenicity,
            "route": "dermal",
            "unit": "-",
            "species": "-",
            "effect": "cancer",
            "severity": "high",
            "source": tox.source,
            "confidence": tox.confidence_score,
        })
    return hazards

async def upsert_ingredient_from_identity(result: ChemicalIdentityResult):
    if not result or not result.found or not result.comprehensive_data:
        return
    basic = result.comprehensive_data.basic_identifiers
    tox = result.comprehensive_data.toxicology
    key = _ingredient_key(basic, tox, result.inci_name)

    await neo4j_client.run("""
    MERGE (i:Ingredient {key: $key})
    SET i.inci = $inci,
        i.cas = $cas,
        i.inchi_key = $inchi_key,
        i.dtxsid = $dtxsid
    """, {
        "key": key,
        "inci": result.inci_name,
        "cas": basic.cas_number if basic else None,
        "inchi_key": basic.inchi_key if basic else None,
        "dtxsid": tox.dtxsid if tox else None
    })

    if tox:
        hazards = _hazards_from_tox(tox)
        if hazards:
            await neo4j_client.run("""
            MATCH (i:Ingredient {key: $key})
            WITH i, $hazards AS hz
            UNWIND hz AS h
              MERGE (z:Hazard {
                type: h.type,
                route: toLower(h.route),
                unit: h.unit,
                species: h.species,
                value: h.value
              })
              SET z.severity = h.severity,
                  z.source = h.source,
                  z.confidence = h.confidence
              MERGE (i)-[:HAS_HAZARD]->(z)
              FOREACH (e IN CASE WHEN h.effect IS NULL THEN [] ELSE [h.effect] END |
                MERGE (ef:Effect {name: e})
                MERGE (z)-[:CAUSES]->(ef)
              )
            """, {"key": key, "hazards": hazards})

async def upsert_product(product_id: str, ingredient_keys: List[str]):
    await neo4j_client.run("""
    MERGE (p:Product {id: $pid})
    WITH p, $keys AS ks
    UNWIND ks AS k
      MERGE (i:Ingredient {key: k})
      MERGE (p)-[:CONTAINS]->(i)
    """, {"pid": product_id, "keys": ingredient_keys})


async def upsert_hed_assessment(inci_name: str, neo4j_hed_data: Dict[str, Any], ingredient_key: Optional[str] = None):
    """
    Upsert HED (Human Equivalent Dose) assessment data to Neo4j.
    
    Creates/updates:
    - HEDAssessment node with toxicological safety calculations
    - Links to Ingredient node via HAS_HED_ASSESSMENT relationship
    
    Args:
        inci_name: INCI name of the ingredient
        neo4j_hed_data: HED data from HEDIntegrationService.prepare_neo4j_data()
        ingredient_key: Optional ingredient key (from upsert_ingredient_from_identity)
    """
    if not neo4j_hed_data.get("hed_available"):
        # No HED data available - optionally record this
        return
    
    # Add timestamp
    timestamp = datetime.utcnow().isoformat()
    
    await neo4j_client.run("""
    // Find existing ingredient by inci name (case-insensitive)
    MATCH (i:Ingredient)
    WHERE toLower(i.inci) = toLower($inci_name)
    
    // Create/Update HED Assessment node (unique per ingredient)
    MERGE (h:HEDAssessment {ingredient_key: i.key})
    SET h.dtxsid = $dtxsid,
        h.hed_mg_kg = $hed_mg_kg,
        h.total_safe_dose_mg = $total_safe_dose_mg,
        h.calculation_method = $calculation_method,
        h.source_toxicity_type = $source_toxicity_type,
        h.source_animal_species = $source_animal_species,
        h.source_route = $source_route,
        h.source_effect = $source_effect,
        h.source_value_mg_kg = $source_value_mg_kg,
        h.safe_concentration_percent = $safe_concentration_percent,
        h.max_dermal_application_mg = $max_dermal_application_mg,
        h.safety_factor = $safety_factor,
        h.risk_assessment = $risk_assessment,
        h.recommendation = $recommendation,
        h.total_hed_calculations = $total_hed_calculations,
        h.relevant_entries = $relevant_entries,
        h.last_updated = $timestamp
    
    // Link ingredient to HED assessment
    MERGE (i)-[:HAS_HED_ASSESSMENT]->(h)
    
    // Create/Link to Risk Assessment effect
    WITH i, h, $risk_assessment AS risk_level
    MERGE (e:Effect {name: 'hed_safety_threshold'})
    SET e.description = 'Human Equivalent Dose safety threshold from animal toxicology'
    MERGE (h)-[:ASSESSED_AS {level: risk_level}]->(e)
    """, {
        "inci_name": inci_name,
        "dtxsid": neo4j_hed_data.get("dtxsid"),
        "hed_mg_kg": neo4j_hed_data.get("hed_mg_kg"),
        "total_safe_dose_mg": neo4j_hed_data.get("total_safe_dose_mg"),
        "calculation_method": neo4j_hed_data.get("calculation_method"),
        "source_toxicity_type": neo4j_hed_data.get("source_toxicity_type"),
        "source_animal_species": neo4j_hed_data.get("source_animal_species"),
        "source_route": neo4j_hed_data.get("source_route"),
        "source_effect": neo4j_hed_data.get("source_effect"),
        "source_value_mg_kg": neo4j_hed_data.get("source_value_mg_kg"),
        "safe_concentration_percent": neo4j_hed_data.get("safe_concentration_percent"),
        "max_dermal_application_mg": neo4j_hed_data.get("max_dermal_application_mg"),
        "safety_factor": neo4j_hed_data.get("safety_factor"),
        "risk_assessment": neo4j_hed_data.get("risk_assessment"),
        "recommendation": neo4j_hed_data.get("recommendation"),
        "total_hed_calculations": neo4j_hed_data.get("total_hed_calculations"),
        "relevant_entries": neo4j_hed_data.get("relevant_entries"),
        "timestamp": timestamp,
    })


async def upsert_ingredient_with_hed(result: ChemicalIdentityResult, neo4j_hed_data: Optional[Dict[str, Any]] = None):
    """
    Upsert ingredient from ChemicalIdentityResult and optionally add HED assessment.
    
    This is a convenience method that combines:
    1. upsert_ingredient_from_identity() - adds basic ingredient + hazards
    2. upsert_hed_assessment() - adds HED toxicology assessment
    
    Args:
        result: ChemicalIdentityResult from scraping process
        neo4j_hed_data: Optional HED data from HEDIntegrationService
    """
    # First, upsert basic ingredient data
    await upsert_ingredient_from_identity(result)
    
    # Then, add HED assessment if available
    if neo4j_hed_data and neo4j_hed_data.get("hed_available"):
        await upsert_hed_assessment(result.inci_name, neo4j_hed_data)

async def upsert_user_profile(user_email: str, conditions: List[str] = None, profile_data: dict = None):
    """
    Upsert user profile to Neo4j with comprehensive data.
    
    Args:
        user_email: User identifier
        conditions: Legacy conditions list (for backward compatibility)
        profile_data: Full user profile dict from MongoDB
    """
    # Build profile properties from profile_data if provided
    profile_props = {} # TODO - do we need the new dictionary profile_props if we only map data from profile_data?
    if profile_data:
        # Physiological
        if profile_data.get("age"): profile_props["age"] = profile_data["age"]
        if profile_data.get("gender"): profile_props["gender"] = profile_data["gender"]
        if profile_data.get("weight"): profile_props["weight"] = profile_data["weight"]
        if profile_data.get("height"): profile_props["height"] = profile_data["height"]
        
        # Skin type
        if profile_data.get("skinType"): profile_props["skinType"] = profile_data["skinType"]
        if profile_data.get("sensitiveSkin") is not None: profile_props["sensitiveSkin"] = profile_data["sensitiveSkin"]
        if profile_data.get("atopicSkin") is not None: profile_props["atopicSkin"] = profile_data["atopicSkin"]
        if profile_data.get("acneProne") is not None: profile_props["acneProne"] = profile_data["acneProne"]
        if profile_data.get("barrierDysfunction") is not None: profile_props["barrierDysfunction"] = profile_data["barrierDysfunction"]
        if profile_data.get("seborrheicDermatitis") is not None: profile_props["seborrheicDermatitis"] = profile_data["seborrheicDermatitis"]
        
        # Allergies and intolerances
        if profile_data.get("cosmeticAllergies"): profile_props["cosmeticAllergies"] = profile_data["cosmeticAllergies"]
        if profile_data.get("generalAllergies"): profile_props["generalAllergies"] = profile_data["generalAllergies"]
        if profile_data.get("knownIntolerances"): profile_props["knownIntolerances"] = profile_data["knownIntolerances"]
        if profile_data.get("dermatologistRecommendedAvoid"): profile_props["dermatologistRecommendedAvoid"] = profile_data["dermatologistRecommendedAvoid"]
        
        # Medications
        if profile_data.get("photosensitizingMedications"): profile_props["photosensitizingMedications"] = profile_data["photosensitizingMedications"]
        if profile_data.get("diureticMedications"): profile_props["diureticMedications"] = profile_data["diureticMedications"]
        if profile_data.get("retinoidTherapy") is not None: profile_props["retinoidTherapy"] = profile_data["retinoidTherapy"]
        if profile_data.get("corticosteroidUse"): profile_props["corticosteroidUse"] = profile_data["corticosteroidUse"]
        if profile_data.get("immunosuppressants"): profile_props["immunosuppressants"] = profile_data["immunosuppressants"]
        if profile_data.get("hormonalTherapy"): profile_props["hormonalTherapy"] = profile_data["hormonalTherapy"]
        
        # Cosmetic exposure
        if profile_data.get("productUsageFrequency"): profile_props["productUsageFrequency"] = profile_data["productUsageFrequency"]
        if profile_data.get("typicalApplicationAreas"): profile_props["typicalApplicationAreas"] = profile_data["typicalApplicationAreas"]
        if profile_data.get("preferredProductTypes"): profile_props["preferredProductTypes"] = profile_data["preferredProductTypes"]
        
        # Preferences
        if profile_data.get("preferNatural") is not None: profile_props["preferNatural"] = profile_data["preferNatural"]
        if profile_data.get("veganOnly") is not None: profile_props["veganOnly"] = profile_data["veganOnly"]
        if profile_data.get("fragranceFree") is not None: profile_props["fragranceFree"] = profile_data["fragranceFree"]
        if profile_data.get("avoidCategories"): profile_props["avoidCategories"] = profile_data["avoidCategories"]
        
        # Environment
        if profile_data.get("climateType"): profile_props["climateType"] = profile_data["climateType"]
        if profile_data.get("pollutionExposure"): profile_props["pollutionExposure"] = profile_data["pollutionExposure"]
        if profile_data.get("sunExposure"): profile_props["sunExposure"] = profile_data["sunExposure"]
        if profile_data.get("waterHardness"): profile_props["waterHardness"] = profile_data["waterHardness"]
    
    # Create/update User and UserProfile nodes
    await neo4j_client.run("""
    MERGE (u:User {email: $email})
    SET u.id = $email
    
    // Create/update UserProfile node with all properties
    MERGE (u)-[:HAS_PROFILE]->(up:UserProfile {user_email: $email})
    SET up += $profile_props
    
    // Handle conditions (legacy support)
    WITH u, $conds AS cs
    WHERE cs IS NOT NULL AND size(cs) > 0
    UNWIND cs AS c
      MERGE (cond:Condition {name: c})
      MERGE (u)-[:HAS_CONDITION]->(cond)
    """, {
        "email": user_email,
        "conds": conditions or [],
        "profile_props": profile_props
    })