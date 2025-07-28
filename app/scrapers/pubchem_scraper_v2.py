from typing import Dict, Any, List, Optional
import re
import logging
from .base_scraper import BaseScraper
import pubchempy as pcp

logger = logging.getLogger(__name__)

class PubChemScraperV2(BaseScraper):
    """Scraper for PubChem database using pubchempy library."""
    
    def __init__(self):
        super().__init__(rate_limit=0.1)  # Can use faster rate with official library
    
    async def search_by_name(self, name: str) -> Dict[str, Any]:
        """Search PubChem by compound name."""
        try:
            compounds = pcp.get_compounds(name, 'name')
            
            if not compounds:
                return {"source": "pubchem", "found": False, "inci_name": name}
            
            compound = compounds[0]
            
            result = {
                "source": "pubchem",
                "found": True,
                "inci_name": name,
                "smiles": compound.canonical_smiles,
                "inchi": compound.inchi,
                "inchi_key": compound.inchikey,
                "molecular_formula": compound.molecular_formula,
                "molecular_weight": float(compound.molecular_weight) if compound.molecular_weight else None,
                "confidence_score": 0.8  # Consistent with original scraper
            }
            
            cas_number = self._extract_cas_number(compound.synonyms)
            if cas_number:
                result["cas_number"] = cas_number
            
            ec_number = self._extract_ec_number(compound.synonyms)
            if ec_number:
                result["ec_number"] = ec_number
                
            if hasattr(compound, 'iupac_name'):
                result["systematic_name"] = compound.iupac_name
            
            return result
            
        except Exception as e:
            logger.error(f"Error in PubChemScraperV2.search_by_name: {str(e)}")
            return {
                "source": "pubchem",
                "found": False,
                "error": str(e),
                "inci_name": name
            }
    
    async def search_by_cas(self, cas_number: str) -> Dict[str, Any]:
        """Search PubChem by CAS number."""
        try:
            compounds = pcp.get_compounds(cas_number, 'name')  # CAS works as a name search
            
            if not compounds:
                return {"source": "pubchem", "found": False, "cas_number": cas_number}
            
            compound = compounds[0]
            
            result = {
                "source": "pubchem",
                "found": True,
                "cas_number": cas_number,
                "smiles": compound.canonical_smiles,
                "inchi": compound.inchi,
                "inchi_key": compound.inchikey,
                "molecular_formula": compound.molecular_formula,
                "molecular_weight": float(compound.molecular_weight) if compound.molecular_weight else None,
                "confidence_score": 0.9  # Higher confidence since searching by CAS
            }
            
            if hasattr(compound, 'synonyms') and compound.synonyms:
                possible_names = [s for s in compound.synonyms if not self._is_cas_number(s) and not self._is_ec_number(s)]
                if possible_names:
                    result["inci_name"] = possible_names[0]
            
            if hasattr(compound, 'iupac_name'):
                result["systematic_name"] = compound.iupac_name
                
            ec_number = self._extract_ec_number(compound.synonyms)
            if ec_number:
                result["ec_number"] = ec_number
                
            return result
            
        except Exception as e:
            logger.error(f"Error in PubChemScraperV2.search_by_cas: {str(e)}")
            return {
                "source": "pubchem",
                "found": False,
                "error": str(e),
                "cas_number": cas_number
            }
    
    def _is_cas_number(self, text: str) -> bool:
        """Check if a string matches CAS number pattern."""
        return bool(re.match(r'^\d{1,7}-\d{2}-\d$', text))
    
    def _is_ec_number(self, text: str) -> bool:
        """Check if a string matches EC number pattern."""
        return bool(re.match(r'^\d{3}-\d{3}-\d{1,2}$', text))
    
    def _extract_cas_number(self, synonyms: List[str]) -> Optional[str]:
        """Extract CAS number from a list of synonyms."""
        if not synonyms:
            return None
            
        for synonym in synonyms:
            if self._is_cas_number(synonym):
                return synonym
                
        return None
        
    def _extract_ec_number(self, synonyms: List[str]) -> Optional[str]:
        """Extract EC number from a list of synonyms."""
        if not synonyms:
            return None
            
        for synonym in synonyms:
            if self._is_ec_number(synonym):
                return synonym
                
        return None