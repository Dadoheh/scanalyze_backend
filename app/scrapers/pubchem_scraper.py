from typing import Dict, Any
import json
from .base_scraper import BaseScraper

class PubChemScraper(BaseScraper):
    """Scraper for PubChem database via REST API."""
    
    BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    
    def __init__(self):
        super().__init__(rate_limit=1.0)
        
    async def search_by_name(self, name: str) -> Dict[str, Any]:
        """
        Search PubChem by compound name.
        
        Args:
            name: Chemical compound name (INCI)
            
        Returns:
            Dictionary with PubChem data
        """
        # CID (Compound ID) by name
        cid_url = f"{self.BASE_URL}/compound/name/{name}/cids/JSON"
        
        try:
            response = await self._make_request(cid_url)
            cid_data = response.json()
            
            if not cid_data.get("IdentifierList", {}).get("CID"):
                return {"source": "pubchem", "found": False, "inci_name": name}
                
            cid = cid_data["IdentifierList"]["CID"][0]
            
            properties_url = f"{self.BASE_URL}/compound/cid/{cid}/property/MolecularFormula,MolecularWeight,CanonicalSMILES,InChI,InChIKey/JSON"
            prop_response = await self._make_request(properties_url)
            properties = prop_response.json()

            synonyms_url = f"{self.BASE_URL}/compound/cid/{cid}/synonyms/JSON"
            syn_response = await self._make_request(synonyms_url)
            synonyms_data = syn_response.json()
            
            return self._parse_pubchem_data(properties, synonyms_data, name)
            
        except Exception as e:
            return {
                "source": "pubchem",
                "found": False,
                "error": str(e),
                "inci_name": name
            }
    
    async def search_by_cas(self, cas_number: str) -> Dict[str, Any]:
        """Search PubChem by CAS number."""
        return await self.search_by_name(cas_number)
    
    def _parse_pubchem_data(self, properties: Dict, synonyms: Dict, search_term: str) -> Dict[str, Any]:
        """Parse PubChem API response."""
        result = {
            "source": "pubchem",
            "inci_name": search_term,
            "found": True,
            "confidence_score": 0.8
        }
        
    
        if properties.get("PropertyTable", {}).get("Properties"):
            prop = properties["PropertyTable"]["Properties"][0]
                
            result.update({
                "smiles": prop.get("CanonicalSMILES"),
                "inchi": prop.get("InChI"),
                "inchi_key": prop.get("InChIKey"),
                "molecular_formula": prop.get("MolecularFormula"),
                "molecular_weight": prop.get("MolecularWeight")
            })
        
        if synonyms.get("InformationList", {}).get("Information"):
            synonym_list = synonyms["InformationList"]["Information"][0].get("Synonym", [])
            cas_pattern = r'\b\d{2,7}-\d{2}-\d\b'
            
            import re
            for synonym in synonym_list:
                if re.match(cas_pattern, str(synonym)):
                    result["cas_number"] = str(synonym)
                    break
        
        return result
