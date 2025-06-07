from typing import Dict, Any, Optional
import re
from .base_scraper import BaseScraper

class CosIngScraper(BaseScraper):
    """Scraper for EU CosIng database (Cosmetic Ingredient Database)."""
    
    BASE_URL = "https://ec.europa.eu/growth/tools-databases/cosing"
    
    def __init__(self):
        super().__init__(rate_limit=2.0)
    
    async def search_by_name(self, name: str) -> Dict[str, Any]:
        """
        Search CosIng database by INCI name.
        
        Args:
            name: INCI ingredient name
            
        Returns:
            Dictionary with ingredient data from CosIng
        """
        search_url = f"{self.BASE_URL}/index.cfm"
        params = {
            "fuseaction": "search.results",
            "search": name.strip(),
            "dosearch": "1"
        }
        
        try: 
            response = await self._make_request(search_url, params=params)
            html_content = response.text
            parsed_data = self._parse_cosing_response(html_content, name)
            return parsed_data
            
        except Exception as e:
            return {
                "source": "cosing",
                "found": False,
                "error": str(e),
                "inci_name": name
            }
            
    async def search_by_cas(self, cas_number: str) -> Dict[str, Any]:
        """Search by CAS number in Cosing."""
        return await self.search_by_name(cas_number)
    
    def _parse_cosing_response(self, html_content: str, search_term: str) -> Dict[str, Any]:
        """
        Parse CosIng HTML response to extract chemical identifiers.
        
        Args:
            html_content: Raw HTML from CosIng
            search_term: Original search term
            
        Returns:
            Parsed data dictionary
        """
        result = {
            "source": "cosing",
            "inci_name": search_term,
            "found": False,
            "cas_number": None,
            "ec_number": None,
            "systematic_name": None,
            "confidence_score": 0.0
        }
        
        cas_pattern = r'\b\d{2,7}-\d{2}-\d\b'
        cas_matches = re.findall(cas_pattern, html_content)
        
        # EC number pattern: XXX-XXX-X
        ec_pattern = r'\b\d{3}-\d{3}-\d\b'
        ec_matches = re.findall(ec_pattern, html_content)
        
        if cas_matches:
            result["cas_number"] = cas_matches[0]  # Take first match
            result["found"] = True
            result["confidence_score"] = 0.9  # High confidence for official EU source
            
        if ec_matches:
            result["ec_number"] = ec_matches[0]
            
        return result