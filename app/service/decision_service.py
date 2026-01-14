"""
Advanced Decision Engine for Cosmetic Product Safety Assessment

This module implements a sophisticated multi-level risk assessment system that combines:
- User profile data (conditions, allergies, medications, preferences)
- HED (Human Equivalent Dose) toxicological safety data
- Ingredient blacklists (known intolerances, dermatologist recommendations)
- Skin condition × ingredient effect interactions
- Environmental and lifestyle factors

Risk Scoring System:
- 0-30: LOW (safe)
- 31-60: MODERATE (caution advised)
- 61-85: HIGH (not recommended)
- 86-100: CRITICAL (avoid)

Version: 2.0
Author: Scanalyze Backend Team
Last Updated: 2026-01-09
"""

from typing import List, Dict, Any, Optional
from app.core.neo4j_client import neo4j_client
import logging

logger = logging.getLogger(__name__)


class DecisionEngine:
    """Advanced cosmetic safety decision engine with multi-factor risk assessment."""
    
    # Risk score thresholds
    THRESHOLD_LOW = 30
    THRESHOLD_MODERATE = 60
    THRESHOLD_HIGH = 85
    
    # Weight factors for risk calculation
    WEIGHT_BLACKLIST = 1.0  # Absolute override (user-specific intolerances)
    WEIGHT_HED_SAFETY = 0.35  # HED toxicological assessment
    WEIGHT_PROFILE_MATCH = 0.25  # Skin condition × effect matching
    WEIGHT_MEDICATION_INTERACTION = 0.20  # Drug-cosmetic interactions
    WEIGHT_PREFERENCE_VIOLATION = 0.15  # User preference violations
    WEIGHT_ENVIRONMENTAL = 0.05  # Environmental risk modifiers
    
    @staticmethod
    async def decide_product(
        user_email: str,
        product_id: str,
        preferred_routes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive product safety decision for a specific user.
        
        Args:
            user_email: User identifier
            product_id: Product identifier
            preferred_routes: Exposure routes to consider (default: ["dermal"])
            
        Returns:
            {
                "overall_risk": "LOW|MODERATE|HIGH|CRITICAL",
                "risk_score": 0-100,
                "recommendation": "Safe to use|Use with caution|Not recommended|Avoid",
                "ingredients": [
                    {
                        "inci": "Aqua",
                        "risk_level": "LOW",
                        "risk_score": 5,
                        "reasons": [...],
                        "hed_assessment": {...}
                    }
                ],
                "summary": {
                    "critical_count": 0,
                    "high_count": 1,
                    "moderate_count": 3,
                    "low_count": 10
                }
            }
        """
        routes = [r.lower() for r in (preferred_routes or ["dermal"])]
        
        # Get ingredient-level assessments
        ingredients_assessment = await DecisionEngine._assess_ingredients(
            user_email, product_id, routes
        )
        
        # Calculate overall product risk
        overall_score, summary = DecisionEngine._calculate_overall_risk(ingredients_assessment)
        
        # Generate recommendation
        risk_level = DecisionEngine._get_risk_level(overall_score)
        recommendation = DecisionEngine._get_recommendation(risk_level, summary)
        
        return {
            "overall_risk": risk_level,
            "risk_score": overall_score,
            "recommendation": recommendation,
            "ingredients": ingredients_assessment,
            "summary": summary
        }
    
    @staticmethod
    async def _assess_ingredients(
        user_email: str,
        product_id: str,
        routes: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Assess each ingredient in the product against user profile.
        
        Returns list of ingredient assessments with risk scores and reasons.
        """
        cypher = """
        // 1. Get user profile (comprehensive)
        MATCH (u:User {email: $user_email})
        OPTIONAL MATCH (u)-[:HAS_PROFILE]->(up:UserProfile)
        
        // 2. Get user conditions
        OPTIONAL MATCH (u)-[:HAS_CONDITION]->(c:Condition)
        WITH u, up, collect(DISTINCT c.name) AS conditions
        
        // 3. Get product ingredients
        MATCH (p:Product {id: $product_id})-[:CONTAINS]->(i:Ingredient)
        
        // 4. Get HED assessment for ingredient
        OPTIONAL MATCH (i)-[:HAS_HED_ASSESSMENT]->(hed:HEDAssessment)
        
        // 5. Get hazards for this ingredient (if any)
        OPTIONAL MATCH (i)-[:HAS_HAZARD]->(h:Hazard)
        WHERE h.route IN $routes
        OPTIONAL MATCH (h)-[:CAUSES]->(e:Effect)
        
        // 5a. Collect effects per hazard first (avoid nested aggregates)
        WITH u, up, conditions, i, hed, h, collect(DISTINCT e.name) AS effect_names
        
        // 5b. Now collect hazards with their effects
        WITH u, up, conditions, i, hed,
             collect(DISTINCT {
                 type: h.type,
                 severity: h.severity,
                 route: h.route,
                 effects: effect_names
             }) AS hazards
        
        // 6. Extract user profile details
        WITH i, hed, hazards, conditions,
             coalesce(up.knownIntolerances, []) AS known_intolerances,
             coalesce(up.dermatologistRecommendedAvoid, []) AS dermatologist_avoid,
             coalesce(up.cosmeticAllergies, []) AS cosmetic_allergies,
             coalesce(up.photosensitizingMedications, []) AS photosensitizing_meds,
             coalesce(up.retinoidTherapy, false) AS retinoid_therapy,
             coalesce(up.corticosteroidUse, 'none') AS corticosteroid_use,
             coalesce(up.barrierDysfunction, false) AS barrier_dysfunction,
             coalesce(up.sensitiveSkin, false) AS sensitive_skin,
             coalesce(up.atopicSkin, false) AS atopic_skin,
             coalesce(up.acneProne, false) AS acne_prone,
             coalesce(up.avoidCategories, []) AS avoid_categories,
             coalesce(up.fragranceFree, false) AS fragrance_free,
             coalesce(up.veganOnly, false) AS vegan_only,
             coalesce(up.preferNatural, false) AS prefer_natural,
             coalesce(up.sunExposure, 'moderate') AS sun_exposure,
             coalesce(up.pollutionExposure, 'moderate') AS pollution_exposure
        
        // 7. Calculate risk components
        WITH i, hed, hazards, conditions,
             known_intolerances, dermatologist_avoid, cosmetic_allergies,
             photosensitizing_meds, retinoid_therapy, corticosteroid_use,
             barrier_dysfunction, sensitive_skin, atopic_skin, acne_prone,
             avoid_categories, fragrance_free, vegan_only, prefer_natural,
             sun_exposure, pollution_exposure,
             
             // BLACKLIST CHECK (absolute priority)
             CASE 
                 WHEN toLower(i.inci) IN [x IN known_intolerances | toLower(x)] THEN 100
                 WHEN toLower(i.inci) IN [x IN dermatologist_avoid | toLower(x)] THEN 95
                 ELSE 0
             END AS blacklist_score,
             
             // HED SAFETY ASSESSMENT
             CASE 
                 WHEN hed.risk_assessment = 'CRITICAL' THEN 90
                 WHEN hed.risk_assessment = 'HIGH' THEN 70
                 WHEN hed.risk_assessment = 'MODERATE' THEN 45
                 WHEN hed.risk_assessment = 'LOW' THEN 15
                 ELSE 25  // No HED data available - moderate baseline
             END AS hed_risk_score,
             
             // PROFILE MATCHING (conditions × effects)
             CASE
                 // Sensitive/atopic skin + irritation/sensitization
                 WHEN (sensitive_skin OR atopic_skin) AND 
                      ANY(h IN hazards WHERE 'irritation' IN h.effects OR 'sensitization' IN h.effects) 
                 THEN 75
                 
                 // Barrier dysfunction + high penetration risk
                 WHEN barrier_dysfunction AND 
                      ANY(h IN hazards WHERE h.severity = 'high')
                 THEN 70
                 
                 // Acne-prone + comedogenic effects
                 WHEN acne_prone AND 
                      ANY(h IN hazards WHERE 'comedogenic' IN h.effects)
                 THEN 60
                 
                 // Rosacea/sensitive + fragrance
                 WHEN (sensitive_skin OR 'rosacea' IN conditions) AND
                      (toLower(i.inci) CONTAINS 'parfum' OR toLower(i.inci) CONTAINS 'fragrance')
                 THEN 65
                 
                 // Eczema/psoriasis + irritants
                 WHEN ('eczema' IN conditions OR 'psoriasis' IN conditions) AND
                      ANY(h IN hazards WHERE 'irritation' IN h.effects)
                 THEN 70
                 
                 // General allergies + sensitizers
                 WHEN size(cosmetic_allergies) > 0 AND
                      ANY(h IN hazards WHERE 'sensitization' IN h.effects)
                 THEN 55
                 
                 ELSE 20  // Baseline for no specific matches
             END AS profile_match_score,
             
             // MEDICATION INTERACTIONS
             CASE
                 // Photosensitizing drugs + photosensitizing ingredients
                 WHEN size(photosensitizing_meds) > 0 AND
                      (sun_exposure = 'high_outdoor') AND
                      ANY(h IN hazards WHERE 'photosensitivity' IN h.effects)
                 THEN 85
                 
                 // Retinoid therapy + AHAs/BHAs/Vitamin C
                 WHEN retinoid_therapy AND
                      (toLower(i.inci) CONTAINS 'acid' OR 
                       toLower(i.inci) CONTAINS 'ascorbic' OR
                       toLower(i.inci) CONTAINS 'retinol')
                 THEN 60
                 
                 // Corticosteroid use + barrier weakening
                 WHEN corticosteroid_use IN ['topical', 'both'] AND
                      barrier_dysfunction
                 THEN 50
                 
                 ELSE 10
             END AS medication_interaction_score,
             
             // PREFERENCE VIOLATIONS (milder penalty)
             CASE
                 WHEN fragrance_free AND 
                      (toLower(i.inci) CONTAINS 'parfum' OR toLower(i.inci) CONTAINS 'fragrance')
                 THEN 40
                 
                 WHEN 'parabens' IN avoid_categories AND
                      toLower(i.inci) CONTAINS 'paraben'
                 THEN 35
                 
                 WHEN 'sulfates' IN avoid_categories AND
                      (toLower(i.inci) CONTAINS 'sulfate' OR toLower(i.inci) = 'sls' OR toLower(i.inci) = 'sles')
                 THEN 35
                 
                 WHEN 'silicones' IN avoid_categories AND
                      (toLower(i.inci) CONTAINS 'siloxane' OR toLower(i.inci) CONTAINS 'dimethicone')
                 THEN 30
                 
                 ELSE 5
             END AS preference_violation_score,
             
             // ENVIRONMENTAL RISK MODIFIERS
             CASE
                 WHEN pollution_exposure = 'high' AND
                      ANY(h IN hazards WHERE 'oxidative_stress' IN h.effects)
                 THEN 25
                 
                 WHEN sun_exposure = 'high_outdoor' AND
                      ANY(h IN hazards WHERE 'photodegradation' IN h.effects OR 'photosensitivity' IN h.effects)
                 THEN 30
                 
                 ELSE 5
             END AS environmental_risk_score
        
        // 8. Aggregate risk score with weighted formula
        WITH i, hed, hazards,
             blacklist_score, hed_risk_score, profile_match_score,
             medication_interaction_score, preference_violation_score, environmental_risk_score,
             
             // If blacklisted, override everything
             CASE 
                 WHEN blacklist_score >= 90 THEN blacklist_score
                 ELSE round(
                     hed_risk_score * $weight_hed +
                     profile_match_score * $weight_profile +
                     medication_interaction_score * $weight_medication +
                     preference_violation_score * $weight_preference +
                     environmental_risk_score * $weight_environmental
                 )
             END AS final_risk_score
        
        // 9. Collect reasons for the risk score
        WITH i, hed, hazards, final_risk_score,
             blacklist_score, hed_risk_score, profile_match_score,
             medication_interaction_score, preference_violation_score, environmental_risk_score,
             
             // Build reasons list
             [
                 CASE WHEN blacklist_score >= 90 THEN 'Ingredient on your personal blacklist' ELSE null END,
                 CASE WHEN blacklist_score >= 90 THEN null
                      WHEN hed_risk_score >= 70 THEN 'High toxicological risk (HED assessment)'
                      WHEN hed_risk_score >= 45 THEN 'Moderate toxicological concern'
                      ELSE null END,
                 CASE WHEN profile_match_score >= 60 THEN 'Not suitable for your skin condition' ELSE null END,
                 CASE WHEN medication_interaction_score >= 60 THEN 'May interact with your medications' ELSE null END,
                 CASE WHEN preference_violation_score >= 30 THEN 'Violates your ingredient preferences' ELSE null END,
                 CASE WHEN environmental_risk_score >= 25 THEN 'Environmental risk factor' ELSE null END
             ] AS reasons
        
        // 10. Return results
        RETURN 
            i.inci AS inci,
            i.key AS ingredient_key,
            final_risk_score AS risk_score,
            CASE 
                WHEN final_risk_score >= 86 THEN 'CRITICAL'
                WHEN final_risk_score >= 61 THEN 'HIGH'
                WHEN final_risk_score >= 31 THEN 'MODERATE'
                ELSE 'LOW'
            END AS risk_level,
            [r IN reasons WHERE r IS NOT NULL] AS reasons,
            {
                blacklist: blacklist_score,
                hed: hed_risk_score,
                profile_match: profile_match_score,
                medication: medication_interaction_score,
                preference: preference_violation_score,
                environmental: environmental_risk_score
            } AS score_breakdown,
            CASE WHEN hed IS NOT NULL THEN {
                hed_mg_kg: hed.hed_mg_kg,
                safe_concentration_percent: hed.safe_concentration_percent,
                risk_assessment: hed.risk_assessment,
                recommendation: hed.recommendation,
                source_species: hed.source_animal_species,
                source_type: hed.source_toxicity_type
            } ELSE null END AS hed_assessment
        ORDER BY risk_score DESC
        """
        
        params = {
            "user_email": user_email,
            "product_id": product_id,
            "routes": routes,
            "weight_hed": DecisionEngine.WEIGHT_HED_SAFETY,
            "weight_profile": DecisionEngine.WEIGHT_PROFILE_MATCH,
            "weight_medication": DecisionEngine.WEIGHT_MEDICATION_INTERACTION,
            "weight_preference": DecisionEngine.WEIGHT_PREFERENCE_VIOLATION,
            "weight_environmental": DecisionEngine.WEIGHT_ENVIRONMENTAL
        }
        
        results = await neo4j_client.run(cypher, params)
        logger.info(f"Assessed {len(results)} ingredients for product {product_id}, user {user_email}")
        
        return results
    
    @staticmethod
    def _calculate_overall_risk(ingredients: List[Dict[str, Any]]) -> tuple[int, Dict[str, int]]:
        """
        Calculate overall product risk score from ingredient assessments.
        
        Uses weighted average with critical/high ingredients having more impact.
        
        Returns:
            (overall_score, summary_dict)
        """
        if not ingredients:
            return 0, {"critical_count": 0, "high_count": 0, "moderate_count": 0, "low_count": 0}
        
        summary = {
            "critical_count": sum(1 for i in ingredients if i["risk_level"] == "CRITICAL"),
            "high_count": sum(1 for i in ingredients if i["risk_level"] == "HIGH"),
            "moderate_count": sum(1 for i in ingredients if i["risk_level"] == "MODERATE"),
            "low_count": sum(1 for i in ingredients if i["risk_level"] == "LOW")
        }
        
        # If any critical ingredient, product is critical
        if summary["critical_count"] > 0:
            max_critical_score = max(i["risk_score"] for i in ingredients if i["risk_level"] == "CRITICAL")
            return max_critical_score, summary
        
        # Weighted average: high-risk ingredients count more
        weighted_sum = 0
        weight_sum = 0
        
        for ing in ingredients:
            score = ing["risk_score"]
            # Higher scores get exponentially more weight
            if score >= 61:
                weight = 3.0  # High risk
            elif score >= 31:
                weight = 2.0  # Moderate risk
            else:
                weight = 1.0  # Low risk
            
            weighted_sum += score * weight
            weight_sum += weight
        
        overall_score = round(weighted_sum / weight_sum) if weight_sum > 0 else 0
        
        return overall_score, summary
    
    @staticmethod
    def _get_risk_level(score: int) -> str:
        """Convert numeric score to risk level category."""
        if score >= DecisionEngine.THRESHOLD_HIGH:
            return "CRITICAL"
        elif score >= DecisionEngine.THRESHOLD_MODERATE:
            return "HIGH"
        elif score >= DecisionEngine.THRESHOLD_LOW:
            return "MODERATE"
        else:
            return "LOW"
    
    @staticmethod
    def _get_recommendation(risk_level: str, summary: Dict[str, int]) -> str:
        """Generate user-friendly recommendation based on risk assessment."""
        if risk_level == "CRITICAL":
            return "Avoid this product - contains ingredients unsuitable for your profile"
        
        if risk_level == "HIGH":
            if summary["critical_count"] > 0 or summary["high_count"] >= 3:
                return "Not recommended - multiple high-risk ingredients detected"
            else:
                return "Use with extreme caution - consult dermatologist first"
        
        if risk_level == "MODERATE":
            if summary["high_count"] > 0:
                return "Use with caution - some ingredients may cause issues"
            else:
                return "Generally safe, but monitor for reactions"
        
        # LOW risk
        if summary["moderate_count"] == 0:
            return "Safe to use - all ingredients suitable for your profile"
        else:
            return "Safe to use - minor considerations noted"


# Backward compatibility: expose decide_product as module function
async def decide_product(
    user_email: str,
    product_id: str,
    preferred_routes: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Main entry point for product safety decision.
    
    See DecisionEngine.decide_product() for full documentation.
    """
    return await DecisionEngine.decide_product(user_email, product_id, preferred_routes)