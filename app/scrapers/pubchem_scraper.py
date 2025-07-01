from typing import Dict, Any
import json
from .base_scraper import BaseScraper

class PubChemScraper(BaseScraper):
    """Scraper for PubChem database via REST API."""
    
    BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    
    def __init__(self):
        super().__init__(rate_limit=1.0)
        
    async def search_by_name(self, name: str) -> Dict[str, Any]:
        """Search PubChem by compound name."""
        cid_url = f"{self.BASE_URL}/compound/name/{name}/cids/JSON"
        
        try:
            response = await self._make_request(cid_url)
            cid_data = response.json()
            
            if not cid_data.get("IdentifierList", {}).get("CID"):
                return {"source": "pubchem", "found": False, "inci_name": name}
                
            cid = cid_data["IdentifierList"]["CID"][0]
            
            properties = await self._get_properties_separately(cid)
            synonyms_data = await self._get_synonyms(cid)
            
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
    
    async def _get_properties_separately(self, cid: int) -> Dict[str, Any]:
        """Get properties with separate API calls to avoid 400 errors."""
        properties = {}
        
        property_endpoints = [
            ("MolecularFormula", "molecular_formula"),
            ("MolecularWeight", "molecular_weight"),
            ("CanonicalSMILES", "smiles"),
            ("InChI", "inchi"),
            ("InChIKey", "inchi_key")
        ]
        
        for pubchem_prop, our_prop in property_endpoints:
            try:
                prop_url = f"{self.BASE_URL}/compound/cid/{cid}/property/{pubchem_prop}/JSON"
                response = await self._make_request(prop_url)
                data = response.json()
                
                if data.get("PropertyTable", {}).get("Properties"):
                    prop_value = data["PropertyTable"]["Properties"][0].get(pubchem_prop)
                    if prop_value:
                        properties[our_prop] = prop_value
                        
            except Exception as e:
                #logger.warning(f"Failed to get {pubchem_prop} for CID {cid}: {e}")
                continue
        
        return {"PropertyTable": {"Properties": [properties]}} if properties else {}
    
    async def _get_synonyms(self, cid: int) -> Dict[str, Any]:
        """Get synonyms separately."""
        try:
            synonyms_url = f"{self.BASE_URL}/compound/cid/{cid}/synonyms/JSON"
            response = await self._make_request(synonyms_url)
            return response.json()
        except Exception as e:
            #logger.warning(f"Failed to get synonyms for CID {cid}: {e}")
            return {}

    def _parse_pubchem_data(self, properties: Dict, synonyms: Dict, search_term: str) -> Dict[str, Any]:
        """Parse PubChem API response - updated for new format."""
        result = {
            "source": "pubchem",
            "inci_name": search_term,
            "found": False,
            "confidence_score": 0.8
        }
        
        # Check if we have any properties
        if properties.get("PropertyTable", {}).get("Properties"):
            prop = properties["PropertyTable"]["Properties"][0]
            result["found"] = True
            
            result.update({
                "smiles": prop.get("smiles"),
                "inchi": prop.get("inchi"),
                "inchi_key": prop.get("inchi_key"),
                "molecular_formula": prop.get("molecular_formula"),
                "molecular_weight": prop.get("molecular_weight")
            })
        
        # Parse CAS number from synonyms
        if synonyms.get("InformationList", {}).get("Information"):
            synonym_list = synonyms["InformationList"]["Information"][0].get("Synonym", [])
            cas_pattern = r'\b\d{2,7}-\d{2}-\d\b'
            
            import re
            for synonym in synonym_list:
                if re.match(cas_pattern, str(synonym)):
                    result["cas_number"] = str(synonym)
                    result["found"] = True
                    break
        
        return result
