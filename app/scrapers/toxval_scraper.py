from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from ..core.mysql_database import async_session
from ..service.toxval_service import ToxValService
from .base_scraper import BaseScraper

class ToxValScraper(BaseScraper):
    """Scraper for the local MySQL ToxVal database."""
    
    def __init__(self):
        super().__init__()
        self.service = ToxValService()
        self.db = None
    
    async def __aenter__(self):
        """Enter the asynchronous context and initialize the database session."""
        self.db = async_session()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the asynchronous context and close the database session."""
        await self.db.close()
    
    async def search_by_name(self, name: str) -> Dict[str, Any]:
        """Search for a chemical by its INCI name.
        
        Args:
            name (str): The INCI name of the chemical.
        
        Returns:
            Dict[str, Any]: A dictionary containing the search results.
        """
        chemicals = await self.service.find_chemical_by_name(self.db, name)
        
        if not chemicals or len(chemicals) == 0:
            return {"found": False}
            
        # Take the first result as the best match
        chemical = chemicals[0]
        dtxsid = chemical["dtxsid"]
        
        # Gather all data
        skin_eye = await self.service.get_skin_eye_data(self.db, dtxsid)
        cancer = await self.service.get_cancer_data(self.db, dtxsid)
        dermal = await self.service.get_dermal_toxicity(self.db, dtxsid)
        
        # Map to the format expected by ChemicalIdentityMapper
        return {
            "found": True,
            "irritation_potential": self._extract_irritation(skin_eye),
            "sensitization_potential": self._extract_sensitization(skin_eye),
            "carcinogenicity": self._extract_carcinogenicity(cancer),
            "source": "toxval"
        }
    
    async def search_by_cas(self, cas_number: str) -> Dict[str, Any]:
        """Search for a chemical by its CAS number.
        
        Args:
            cas_number (str): The CAS number of the chemical.
        
        Returns:
            Dict[str, Any]: A dictionary containing the search results.
        """
        chemical = await self.service.find_chemical_by_cas(self.db, cas_number)
        
        if not chemical:
            return {"found": False}
            
        dtxsid = chemical["dtxsid"]
        
        # Gather all data
        skin_eye = await self.service.get_skin_eye_data(self.db, dtxsid)
        cancer = await self.service.get_cancer_data(self.db, dtxsid)
        dermal = await self.service.get_dermal_toxicity(self.db, dtxsid)
        
        # Map to the format expected by ChemicalIdentityMapper
        return {
            "found": True,
            "irritation_potential": self._extract_irritation(skin_eye),
            "sensitization_potential": self._extract_sensitization(skin_eye),
            "carcinogenicity": self._extract_carcinogenicity(cancer),
            "source": "toxval"
        }
        
    def _extract_irritation(self, skin_eye_data):
        """Extract irritation potential from skin and eye data."""
        for item in skin_eye_data:
            if "irritation" in item.get("endpoint", "").lower():
                return item.get("result_text")
        return None
        
    def _extract_sensitization(self, skin_eye_data):
        """Extract sensitization potential from skin and eye data."""
        for item in skin_eye_data:
            if "sensitisation" in item.get("endpoint", "").lower():
                return item.get("result_text")
        return None
        
    def _extract_carcinogenicity(self, cancer_data):
        """Extract carcinogenicity information from cancer data."""
        if cancer_data:
            return cancer_data[0].get("cancer_call")
        return None
    