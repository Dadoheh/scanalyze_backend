"""
HED Integration Service - Integrates ToxVal toxicology data with HED Calculator

This service processes animal toxicology data from ToxVal and calculates
Human Equivalent Doses (HED) for cosmetic safety assessment.
"""

from typing import Dict, Any, List, Optional
import logging
from ..utils.hed_calculator import HEDCalculator, Species

logger = logging.getLogger(__name__)


# Mapping ToxVal species strings to HED Calculator Species enum
SPECIES_MAPPING = {
    "rat": Species.RAT,
    "mouse": Species.MOUSE,
    "rabbit": Species.RABBIT,
    "guinea pig": Species.GUINEA_PIG,
    "hamster": Species.HAMSTER,
    "dog": Species.DOG,
    "ferret": Species.FERRET,
    "monkey": Species.MONKEY_RHESUS,
    "rhesus": Species.MONKEY_RHESUS,
    "marmoset": Species.MARMOSET,
    "squirrel monkey": Species.SQUIRREL_MONKEY,
    "baboon": Species.BABOON,
    "micro pig": Species.MICRO_PIG,
    "mini pig": Species.MINI_PIG,
    "human": Species.HUMAN,
}

# Relevant toxicity types for HED calculation
# Prioritized: NOAEL > NOEL > LOAEL > LD50
RELEVANT_TOXICITY_TYPES = {
    "NOAEL": 1,  # Highest priority
    "NOEL": 2,
    "NEL": 3,
    "LOAEL": 4,
    "LOEL": 5,
    "LEL": 6,
    "LD50": 7,  # Lowest priority (acute toxicity)
}

# Routes relevant for dermal/cosmetic assessment
RELEVANT_ROUTES = {
    "oral",
    "dermal",
    "gavage",
    "diet",
    "drinking water",
}

# Units that can be converted to mg/kg or mg/kg-day
CONVERTIBLE_UNITS = {
    "mg/kg",
    "mg/kg-day",
    "mg/kg/day",
    "mg/kg bw/day",
    "mg/kg-bw/day",
}


class HEDIntegrationService:
    """
    Service for integrating ToxVal data with HED Calculator.
    
    Processes animal toxicology data and calculates safe human doses
    for cosmetic ingredient safety assessment.
    """
    
    def __init__(self, human_weight_kg: float = 60.0):
        """
        Initialize HED integration service.
        
        Args:
            human_weight_kg: Reference human body weight (default: 60 kg)
        """
        self.calculator = HEDCalculator(human_weight_kg=human_weight_kg)
        self.human_weight = human_weight_kg
    
    def parse_species(self, species_str: str) -> Optional[Species]:
        """
        Parse species string from ToxVal to Species enum.
        
        Args:
            species_str: Species string from ToxVal (e.g., "Rat", "Mouse")
        
        Returns:
            Species enum or None if not recognized
        """
        if not species_str:
            return None
        
        species_lower = species_str.lower().strip()
        return SPECIES_MAPPING.get(species_lower)
    
    def is_relevant_toxicity_entry(self, entry: Dict[str, Any]) -> bool:
        """
        Check if toxicity entry is relevant for HED calculation.
        
        Args:
            entry: Toxicity value entry from ToxVal
        
        Returns:
            True if entry is relevant for HED calculation
        """
        tox_type = entry.get("type", "").upper()
        route = entry.get("route", "").lower()
        unit = entry.get("unit", "").lower()
        species = entry.get("species", "")
        
        # Check toxicity type
        if tox_type not in RELEVANT_TOXICITY_TYPES:
            return False
        
        # Skip human data (already in human doses)
        if species and species.lower() == "human":
            return False
        
        # Check route
        if route not in RELEVANT_ROUTES:
            return False
        
        # Check unit (must be convertible)
        if unit not in CONVERTIBLE_UNITS and not unit.startswith("ml/kg"):
            return False
        
        return True
    
    def get_toxicity_priority(self, tox_type: str) -> int:
        """
        Get priority score for toxicity type (lower is better).
        
        Args:
            tox_type: Toxicity type (NOAEL, NOEL, LD50, etc.)
        
        Returns:
            Priority score (1 = highest priority)
        """
        return RELEVANT_TOXICITY_TYPES.get(tox_type.upper(), 999)
    
    def process_dermal_toxicity_values(
        self,
        dermal_toxicity_values: List[Dict[str, Any]],
        inci_name: str
    ) -> Dict[str, Any]:
        """
        Process dermal_toxicity_values from ToxVal and calculate HED.
        
        Args:
            dermal_toxicity_values: List of toxicity entries from ToxVal
            inci_name: INCI name of the ingredient
        
        Returns:
            Dictionary with HED calculations and safety assessment
        """
        if not dermal_toxicity_values:
            logger.warning(f"No dermal toxicity values for {inci_name}")
            return {
                "inci_name": inci_name,
                "hed_calculated": False,
                "reason": "No dermal toxicity data available",
                "hed_results": [],
            }
        
        # Filter relevant entries
        relevant_entries = [
            entry for entry in dermal_toxicity_values
            if self.is_relevant_toxicity_entry(entry)
        ]
        
        if not relevant_entries:
            logger.info(f"No relevant toxicity entries for {inci_name}")
            return {
                "inci_name": inci_name,
                "hed_calculated": False,
                "reason": "No relevant animal toxicity data (oral/dermal routes with mg/kg units)",
                "total_entries": len(dermal_toxicity_values),
                "hed_results": [],
            }
        
        # Calculate HED for each relevant entry
        hed_results = []
        for entry in relevant_entries:
            try:
                hed_data = self._calculate_hed_for_entry(entry, inci_name)
                if hed_data:
                    hed_results.append(hed_data)
            except Exception as e:
                logger.warning(f"Failed to calculate HED for entry: {entry}. Error: {e}")
        
        # Sort by toxicity type priority (NOAEL > NOEL > LOAEL > LD50)
        hed_results.sort(key=lambda x: self.get_toxicity_priority(x["original_type"]))
        
        # Get most conservative (lowest HED)
        if hed_results:
            most_conservative = min(hed_results, key=lambda x: x["hed_mg_kg"])
            
            # Calculate safe concentration for cosmetic use
            safety_assessment = self._calculate_cosmetic_safety(most_conservative)
            
            return {
                "inci_name": inci_name,
                "hed_calculated": True,
                "total_entries_processed": len(dermal_toxicity_values),
                "relevant_entries": len(relevant_entries),
                "hed_calculations": len(hed_results),
                "hed_results": hed_results,
                "most_conservative_hed": most_conservative,
                "cosmetic_safety_assessment": safety_assessment,
            }
        else:
            return {
                "inci_name": inci_name,
                "hed_calculated": False,
                "reason": "Failed to calculate HED for any entry",
                "total_entries_processed": len(dermal_toxicity_values),
                "relevant_entries": len(relevant_entries),
                "hed_results": [],
            }
    
    def _calculate_hed_for_entry(
        self,
        entry: Dict[str, Any],
        inci_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate HED for a single toxicity entry.
        
        Args:
            entry: Toxicity entry from ToxVal
            inci_name: INCI name
        
        Returns:
            Dictionary with HED calculation or None if failed
        """
        tox_type = entry.get("type", "")
        value = entry.get("value")
        unit = entry.get("unit", "")
        route = entry.get("route", "")
        species_str = entry.get("species", "")
        effect = entry.get("effect", "-")
        
        # Parse species
        species = self.parse_species(species_str)
        if not species:
            logger.warning(f"Unknown species: {species_str} for {inci_name}")
            return None
        
        # Validate value
        if value is None or value <= 0:
            logger.warning(f"Invalid value: {value} for {inci_name}")
            return None
        
        # Handle unit conversion for mL/kg (e.g., water)
        if unit.lower().startswith("ml/kg"):
            # For water-like substances, approximate: 1 mL ≈ 1 g = 1000 mg
            # This is a rough conversion; ideally need density
            value = value * 1000  # Convert mL/kg to mg/kg
            unit = "mg/kg"
            logger.info(f"Converted {entry['value']} mL/kg to {value} mg/kg for {inci_name}")
        
        # Calculate HED using Km-based method (Eq. 2)
        try:
            hed_mg_kg = self.calculator.calculate_hed_by_km(
                animal_dose_mg_kg=value,
                animal_species=species
            )
            
            # Calculate total safe dose for 60kg human
            total_safe_dose_mg = hed_mg_kg * self.human_weight
            
            return {
                "original_type": tox_type,
                "original_value": entry.get("value"),
                "original_unit": entry.get("unit"),
                "animal_species": species.value,
                "route": route,
                "effect": effect,
                "normalized_value_mg_kg": value,
                "hed_mg_kg": round(hed_mg_kg, 4),
                "total_safe_dose_mg": round(total_safe_dose_mg, 2),
                "calculation_method": "Km-based (Eq. 2)",
                "km_ratio": f"{species.value} Km / Human Km",
            }
        except Exception as e:
            logger.error(f"HED calculation failed for {inci_name}: {e}")
            return None
    
    def _calculate_cosmetic_safety(
        self,
        most_conservative_hed: Dict[str, Any],
        safety_factor: float = 100.0,
        skin_penetration_percent: float = 10.0,
        application_area_cm2: float = 100.0
    ) -> Dict[str, Any]:
        """
        Calculate cosmetic safety parameters from HED.
        
        Args:
            most_conservative_hed: Most conservative HED result
            safety_factor: Safety factor for cosmetics (default: 100)
            skin_penetration_percent: Dermal penetration % (default: 10%)
            application_area_cm2: Application area in cm² (default: 100 cm²)
        
        Returns:
            Dictionary with cosmetic safety assessment
        """
        hed_mg_kg = most_conservative_hed["hed_mg_kg"]
        
        # Use HEDCalculator's assess_dermal_safety method
        # But we already have HED, so we'll calculate directly
        
        # Total safe systemic dose
        safe_systemic_dose_mg = hed_mg_kg * self.human_weight
        
        # Apply safety factor
        safe_dose_with_sf_mg = safe_systemic_dose_mg / safety_factor
        
        # Account for dermal penetration
        penetration_factor = skin_penetration_percent / 100.0
        max_dermal_application_mg = safe_dose_with_sf_mg / penetration_factor
        
        # Calculate safe concentration (mg/cm²)
        safe_concentration_mg_cm2 = max_dermal_application_mg / application_area_cm2
        
        # Convert to % w/w (assuming density ~1 g/cm³)
        safe_concentration_percent = (safe_concentration_mg_cm2 / 10.0)
        
        # Assessment
        if safe_concentration_percent > 100:
            assessment = "SAFE_AT_ANY_CONCENTRATION"
            recommendation = "No concentration limit needed based on toxicology data"
        elif safe_concentration_percent > 10:
            assessment = "SAFE_AT_TYPICAL_USE"
            recommendation = f"Safe at concentrations up to {safe_concentration_percent:.2f}%"
        elif safe_concentration_percent > 1:
            assessment = "SAFE_WITH_LIMITS"
            recommendation = f"Use at concentrations below {safe_concentration_percent:.2f}%"
        elif safe_concentration_percent > 0.1:
            assessment = "REQUIRES_CAREFUL_FORMULATION"
            recommendation = f"Limit to {safe_concentration_percent:.2f}% or less"
        else:
            assessment = "HIGH_RISK"
            recommendation = f"Very low safe concentration: {safe_concentration_percent:.4f}%"
        
        return {
            "hed_mg_kg": hed_mg_kg,
            "safe_systemic_dose_mg": round(safe_systemic_dose_mg, 4),
            "safety_factor_applied": safety_factor,
            "safe_dose_with_sf_mg": round(safe_dose_with_sf_mg, 4),
            "skin_penetration_percent": skin_penetration_percent,
            "max_dermal_application_mg": round(max_dermal_application_mg, 4),
            "application_area_cm2": application_area_cm2,
            "safe_concentration_mg_cm2": round(safe_concentration_mg_cm2, 6),
            "safe_concentration_percent": round(safe_concentration_percent, 4),
            "assessment": assessment,
            "recommendation": recommendation,
            "based_on": {
                "toxicity_type": most_conservative_hed["original_type"],
                "animal_species": most_conservative_hed["animal_species"],
                "route": most_conservative_hed["route"],
            }
        }
    
    def prepare_neo4j_data(
        self,
        hed_integration_result: Dict[str, Any],
        dtxsid: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Prepare HED data for Neo4j insertion.
        
        Args:
            hed_integration_result: Result from process_dermal_toxicity_values()
            dtxsid: Optional DTXSID identifier
        
        Returns:
            Dictionary formatted for Neo4j HEDAssessment nodes
        """
        if not hed_integration_result.get("hed_calculated"):
            return {
                "inci_name": hed_integration_result["inci_name"],
                "hed_available": False,
                "reason": hed_integration_result.get("reason", "Unknown"),
            }
        
        most_conservative = hed_integration_result["most_conservative_hed"]
        safety = hed_integration_result["cosmetic_safety_assessment"]
        
        return {
            "inci_name": hed_integration_result["inci_name"],
            "dtxsid": dtxsid,
            "hed_available": True,
            
            # HED Calculation Results
            "hed_mg_kg": most_conservative["hed_mg_kg"],
            "total_safe_dose_mg": most_conservative["total_safe_dose_mg"],
            "calculation_method": most_conservative["calculation_method"],
            
            # Source Animal Data
            "source_toxicity_type": most_conservative["original_type"],
            "source_animal_species": most_conservative["animal_species"],
            "source_route": most_conservative["route"],
            "source_effect": most_conservative["effect"],
            "source_value_mg_kg": most_conservative["normalized_value_mg_kg"],
            
            # Cosmetic Safety Assessment
            "safe_concentration_percent": safety["safe_concentration_percent"],
            "max_dermal_application_mg": safety["max_dermal_application_mg"],
            "safety_factor": safety["safety_factor_applied"],
            "risk_assessment": safety["assessment"],
            "recommendation": safety["recommendation"],
            
            # Metadata
            "total_hed_calculations": hed_integration_result["hed_calculations"],
            "relevant_entries": hed_integration_result["relevant_entries"],
        }
    
    def process_ingredient_comprehensive_data(
        self,
        comprehensive_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process complete ingredient data from ToxVal scraper and calculate HED.
        
        Args:
            comprehensive_data: Full comprehensive_data dict from scraper results
        
        Returns:
            HED integration result with Neo4j-ready data
        """
        inci_name = comprehensive_data.get("inci_name", "Unknown")
        toxicology = comprehensive_data.get("toxicology", {})
        
        if not toxicology:
            return {
                "inci_name": inci_name,
                "hed_calculated": False,
                "reason": "No toxicology data available",
                "neo4j_data": None,
            }
        
        dermal_toxicity_values = toxicology.get("dermal_toxicity_values", [])
        dtxsid = toxicology.get("dtxsid")
        
        # Process HED
        hed_result = self.process_dermal_toxicity_values(
            dermal_toxicity_values=dermal_toxicity_values,
            inci_name=inci_name
        )
        
        # Prepare Neo4j data
        neo4j_data = self.prepare_neo4j_data(hed_result, dtxsid=dtxsid)
        
        return {
            **hed_result,
            "neo4j_data": neo4j_data,
        }


# Example usage
if __name__ == "__main__":
    # Example from the ToxVal output
    example_aqua_toxicology = {
        "allergen_status": None,
        "phototoxicity_risk": None,
        "irritation_potential": None,
        "sensitization_risk": None,
        "noael_value": 1000.0,
        "safe_concentration": None,
        "dermal_absorption": None,
        "carcinogenicity": None,
        "dermal_toxicity_values": [
            {
                "type": "LD50",
                "value": 90.0,
                "unit": "mL/kg",
                "effect": "-",
                "route": "oral",
                "species": "Rat",
                "risk_class": "-"
            },
            {
                "type": "NOEL",
                "value": 1000.0,
                "unit": "mg/kg-day",
                "effect": "-",
                "route": "oral",
                "species": "Rat",
                "risk_class": "-"
            }
        ],
        "dtxsid": "DTXSID6026296",
        "source": "toxval",
        "confidence_score": 0.8
    }
    
    service = HEDIntegrationService()
    
    print("=== Example: Aqua (Water) ===")
    result = service.process_dermal_toxicity_values(
        dermal_toxicity_values=example_aqua_toxicology["dermal_toxicity_values"],
        inci_name="aqua"
    )
    
    import json
    print(json.dumps(result, indent=2))
    
    if result.get("hed_calculated"):
        print("\n=== Neo4j Data ===")
        neo4j_data = service.prepare_neo4j_data(result, dtxsid="DTXSID6026296")
        print(json.dumps(neo4j_data, indent=2))
