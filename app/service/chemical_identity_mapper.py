from typing import List, Optional, Dict, Any
import asyncio
import time
from ..models.chemical_identity import ChemicalIdentifiers, ChemicalIdentityResult
from ..scrapers.pubchem_scraper import PubChemScraper

class ChemicalIdentityMapper:
    """Main service for mapping INCI names to chemical identifiers."""
    
    def __init__(self):
        self.scrapers = [
            ("pubchem", PubChemScraper),
            # ("comptox", CompToxScraper),  # Will be added later
        ]
    
    async def map_ingredient(self, inci_name: str) -> ChemicalIdentityResult:
        """
        Map single INCI ingredient to chemical identifiers.
        
        Args:
            inci_name: INCI name to map
            
        Returns:
            ChemicalIdentityResult with mapped identifiers
        """
        start_time = time.time()
        result = ChemicalIdentityResult(inci_name=inci_name)
        
        # Try each scraper in priority order
        for source_name, scraper_class in self.scrapers:
            result.sources_checked.append(source_name)
            
            try:
                async with scraper_class() as scraper:
                    data = await scraper.search_by_name(inci_name)
                    
                    if data.get("found", False):
                        # Successfully found data
                        identifiers = ChemicalIdentifiers(
                            inci_name=inci_name,
                            cas_number=data.get("cas_number"),
                            ec_number=data.get("ec_number"),
                            smiles=data.get("smiles"),
                            inchi=data.get("inchi"),
                            inchi_key=data.get("inchi_key"),
                            systematic_name=data.get("systematic_name"),
                            molecular_formula=data.get("molecular_formula"),
                            molecular_weight=data.get("molecular_weight"),
                            source=source_name,
                            confidence_score=data.get("confidence_score", 0.5)
                        )
                        
                        result.identifiers = identifiers
                        result.found = True
                        break  # Stop at first successful result
                        
            except Exception as e:
                result.errors.append(f"{source_name}: {str(e)}")
                continue
        
        result.processing_time_ms = (time.time() - start_time) * 1000

        return result
    
    async def map_ingredients_batch(self, inci_names: List[str]) -> List[ChemicalIdentityResult]:
        """
        Map multiple ingredients concurrently.
        
        Args:
            inci_names: List of INCI names to map
            
        Returns:
            List of mapping results
        """
        # Process in batches to avoid overwhelming external APIs
        batch_size = 5
        results = []
        
        for i in range(0, len(inci_names), batch_size):
            batch = inci_names[i:i + batch_size]
            batch_tasks = [self.map_ingredient(name) for name in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Handle exceptions in batch results
            for result in batch_results:
                if isinstance(result, Exception):
                    # Create error result
                    error_result = ChemicalIdentityResult(
                        inci_name="unknown",
                        found=False,
                        errors=[str(result)]
                    )
                    results.append(error_result)
                else:
                    results.append(result)
            
            # Small delay between batches
            await asyncio.sleep(1.0)
        
        return results
    