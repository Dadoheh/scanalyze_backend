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
                "irritation_potential": self._extract_irritation(skin_eye),
                "sensitization_risk": self._extract_sensitization(skin_eye),
                "carcinogenicity": self._extract_carcinogenicity(cancer),
                "noael_value": noael_value,
                "dermal_toxicity_values": self._extract_toxicity_values_from_toxvaldb(toxvaldb_data),
                "toxicological_effects": self._extract_effects_from_toxvaldb(toxvaldb_data),
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
                "irritation_potential": self._extract_irritation(skin_eye),
                "sensitization_risk": self._extract_sensitization(skin_eye),
                "carcinogenicity": self._extract_carcinogenicity(cancer),
                "noael_value": noael_value,
                "dermal_toxicity_values": self._extract_toxicity_values_from_toxvaldb(toxvaldb_data),
                "toxicological_effects": self._extract_effects_from_toxvaldb(toxvaldb_data),
                "source": "toxval",
                "confidence_score": 0.8
            }
            
            logger.debug(f"ToxValScraper results for CAS {cas_number}: {result}")
            return result
            
        except Exception as e:
            logger.warning(f"Toxicology data failed for toxval: {e}")
            return {"found": False}
            
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
    
    def _extract_noael(self, toxicity_data):
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