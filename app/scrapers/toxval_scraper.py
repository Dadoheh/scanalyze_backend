from typing import Dict, Any, Optional
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.mysql_database import async_session
from ..service.toxval_service import ToxValService
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class ToxValScraper(BaseScraper):
    """Scraper for the local MySQL ToxVal database."""
    
    def __init__(self):
        super().__init__()
        self.service = ToxValService()
        self.db = None
    
    async def __aenter__(self):
        """Enter the asynchronous context and initialize the database session."""
        logger.debug("Initializing ToxValScraper database session")
        self.db = async_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the asynchronous context and close the database session."""
        logger.debug("Closing ToxValScraper database session")
        if self.db:
            await self.db.close()
    
    async def search_by_name(self, name: str) -> Dict[str, Any]: #DRY
        """Search by INCI name."""
        logger.info(f"ToxValScraper: searching by name: {name}")
        try:
            chemicals = await self.service.find_chemical_by_name(self.db, name)
            
            if not chemicals or len(chemicals) == 0:
                logger.info(f"ToxValScraper: No match found for name: {name}")
                return {"found": False}
                
            chemical = chemicals[0]
            dtxsid = chemical["dtxsid"]
            
            logger.info(f"ToxValScraper: Found match for {name}: {chemical['name']} ({chemical['casrn']}, {dtxsid})")
            
            skin_eye = await self.service.get_skin_eye_data(self.db, dtxsid)
            cancer = await self.service.get_cancer_data(self.db, dtxsid)
            dermal = await self.service.get_dermal_toxicity(self.db, dtxsid)
            
            toxvaldb_data = await self.service.get_toxvaldb_data(self.db, dtxsid=dtxsid)
            
            noael_value = self._extract_noael_from_toxvaldb(toxvaldb_data) or self._extract_noael(dermal)
            
            result = {
                "found": True,
                "dtxsid": dtxsid,
                "irritation_potential": self._extract_irritation(skin_eye),
                "sensitization_risk": self._extract_sensitization(skin_eye),
                "allergen_status": self._extract_allergen_status(skin_eye),
                "carcinogenicity": self._extract_carcinogenicity(cancer),
                "noael_value": noael_value,
                "dermal_toxicity_values": self._extract_toxicity_values_from_toxvaldb(toxvaldb_data),
                "toxicological_effects": self._extract_effects_from_toxvaldb(toxvaldb_data),
                "safe_concentration": self._extract_safe_concentration(toxvaldb_data),
                "dermal_absorption": self._extract_dermal_absorption(toxvaldb_data),
                "source": "toxval",
                "confidence_score": 0.8
            }
            
            logger.debug(f"ToxValScraper results for name {name}: {result}")
            return result
            
        except Exception as e:
            logger.warning(f"Toxicology data failed for toxval: {e}")
            return {"found": False}
    
    async def search_by_cas(self, cas_number: str) -> Dict[str, Any]: # DRY
        """Search by CAS number."""
        logger.info(f"ToxValScraper: searching by CAS: {cas_number}")
        try:
            chemical = await self.service.find_chemical_by_cas(self.db, cas_number)
            
            if not chemical:
                logger.info(f"ToxValScraper: No match found for CAS: {cas_number}")
                return {"found": False}
                
            dtxsid = chemical["dtxsid"]
            
            logger.info(f"ToxValScraper: Found match for CAS {cas_number}: {chemical['name']} ({dtxsid})")
            
            # Collect data from different tables
            skin_eye = await self.service.get_skin_eye_data(self.db, dtxsid)
            cancer = await self.service.get_cancer_data(self.db, dtxsid)
            dermal = await self.service.get_dermal_toxicity(self.db, dtxsid)
            
            toxvaldb_data = await self.service.get_toxvaldb_data(self.db, dtxsid=dtxsid)
            
            noael_value = self._extract_noael_from_toxvaldb(toxvaldb_data) or self._extract_noael(dermal)
            
            result = {
                "found": True,
                "dtxsid": dtxsid,
                "irritation_potential": self._extract_irritation(skin_eye),
                "sensitization_risk": self._extract_sensitization(skin_eye),
                "allergen_status": self._extract_allergen_status(skin_eye),
                "carcinogenicity": self._extract_carcinogenicity(cancer),
                "noael_value": noael_value,
                "dermal_toxicity_values": self._extract_toxicity_values_from_toxvaldb(toxvaldb_data),
                "toxicological_effects": self._extract_effects_from_toxvaldb(toxvaldb_data),
                "safe_concentration": self._extract_safe_concentration(toxvaldb_data),
                "dermal_absorption": self._extract_dermal_absorption(toxvaldb_data),
                "source": "toxval",
                "confidence_score": 0.8
            }
            
            logger.debug(f"ToxValScraper results for CAS {cas_number}: {result}")
            return result
            
        except Exception as e:
            logger.warning(f"Toxicology data failed for toxval: {e}")
            return {"found": False}
    


    def _extract_safe_concentration(self, toxvaldb_data):
        """Extract safe concentration values."""
        safety_value_types = ['ADI', 'TDI', 'RfD', 'DNEL', 'PNEC', 'MRL']
        safe_concentrations = []
        
        for item in toxvaldb_data:
            logger.debug(f"Evaluating toxvaldb item for safe concentration: {item}")
            toxval_type = item.get("toxval_type", "")
            matches_safety_type = any(safety_type in toxval_type for safety_type in safety_value_types)
            
            if matches_safety_type and item.get("human_eco") == "human health":
                value = item.get("toxval_numeric")
                unit = item.get("toxval_units", "")
                
                if value is not None:
                    safe_concentrations.append({
                        "value": value,
                        "unit": unit,
                        "type": toxval_type
                    })
        if safe_concentrations:
            primary = safe_concentrations[0]
            return f"{primary['value']} {primary['unit']} ({primary['type']})"
        
        return None

    def _extract_allergen_status(self, skin_eye_data): # todo: improve searching
        """Extract allergen status information from skin_eye data - simplified version."""
        for item in skin_eye_data:
            classification = item.get("classification")
            if classification and "skin sens" in classification.lower():
                logger.debug(f"Found skin sensitization classification: {classification}")
                return classification
            
            endpoint = item.get("endpoint", "")
            if endpoint and "sensitization" in endpoint.lower():
                result_text = item.get("result_text", "")
                if result_text:
                    if "not sensitising" in result_text.lower() or "non-sensitising" in result_text.lower():
                        return "Not sensitizing"
                    elif "sensitising" in result_text.lower() or "sensitizing" in result_text.lower():
                        return "Sensitizing agent"
        
        for item in skin_eye_data:
            result_text = item.get("result_text", "")
            if result_text:
                if "allergen" in result_text.lower() or "allergic" in result_text.lower():
                    return result_text
        
        return None

    def _extract_dermal_absorption(self, toxvaldb_data):
        """Extract dermal absorption percentage with relaxed criteria."""
        for item in toxvaldb_data:
            effect = item.get("toxicological_effect", "").lower()
            route = item.get("exposure_route", "").lower()
            
            if (("absorption" in effect or "penetration" in effect or "permeab" in effect) and
                ("dermal" in route or "cutaneous" in route)):
                return f"{item.get('toxval_numeric')}% absorption"
            
            if (("absorb" in effect or "bioavailab" in effect) and
                ("dermal" in route or "cutaneous" in route or "skin" in route)):
                return f"{item.get('toxval_numeric')} {item.get('toxval_units', '')} (absorption estimate)"
        
        return None
    
    def _extract_irritation(self, skin_eye_data):
        """Extract irritation potential from skin and eye data."""
        for item in skin_eye_data:
            if "irritation" in item.get("endpoint", "").lower():
                logger.debug(f"Found irritation data: {item.get('result_text')}")
                return item.get("result_text")
        logger.debug("No irritation data found")
        return None
        
    def _extract_sensitization(self, skin_eye_data):
        """Extract sensitization potential from skin and eye data."""
        for item in skin_eye_data:
            if "sensitisation" in item.get("endpoint", "").lower():
                logger.debug(f"Found sensitization data: {item.get('result_text')}")
                return item.get("result_text")
        logger.debug("No sensitization data found")
        return None
        
    def _extract_carcinogenicity(self, cancer_data):
        """Extract carcinogenicity information from cancer data."""
        if cancer_data:
            logger.debug(f"Found carcinogenicity data: {cancer_data[0].get('cancer_call')}")
            return cancer_data[0].get("cancer_call")
        logger.debug("No carcinogenicity data found")
        return None
    
    def _extract_noael(self, toxicity_data):  # check it out - we get NOAEL but it returns NONE
        """Extract NOAEL value from toxicity data."""
        for item in toxicity_data:
            if "NOAEL" in item.get("toxval_type", ""):
                return item.get("toxval_numeric")
        return None

    def _extract_noael_from_toxvaldb(self, toxvaldb_data):
        """Extract NOAEL value from toxvaldb data."""
        for item in toxvaldb_data:
            toxval_type = item.get("toxval_type", "").upper()
            if "NOAEL" in toxval_type or "NOEL" in toxval_type:
                return item.get("toxval_numeric")
        return None

    def _extract_toxicity_values_from_toxvaldb(self, toxvaldb_data):
        """Extract structured toxicity values from toxvaldb."""
        result = []
        for item in toxvaldb_data:
            if item.get("toxval_numeric") is not None:
                result.append({
                    "type": item.get("toxval_type"),
                    "value": item.get("toxval_numeric"),
                    "unit": item.get("toxval_units"),
                    "effect": item.get("toxicological_effect"),
                    "route": item.get("exposure_route"),
                    "species": item.get("species_common"),
                    "risk_class": item.get("risk_assessment_class")
                })
        return result if result else None

    def _extract_effects_from_toxvaldb(self, toxvaldb_data):
        """Extract unique toxicological effects from toxvaldb."""
        effects = set()
        for item in toxvaldb_data:
            effect = item.get("toxicological_effect")
            if effect:
                effects.add(effect)
        return list(effects) if effects else None