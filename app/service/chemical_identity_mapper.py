from typing import List, Optional, Dict, Any
import asyncio
import time
import logging
from ..models.chemical_identity import (
    BasicChemicalIdentifiers, ToxicologyData, RegulatoryData, 
    PhysicalChemicalData, ComprehensiveChemicalData, ChemicalIdentityResult
)
from ..scrapers.pubchem_scraper import PubChemScraper
# from ..scrapers.comptox_scraper import CompToxScraper
# from ..scrapers.echa_scraper import ECHAScraper

logger = logging.getLogger(__name__)

class ChemicalIdentityMapper:
    """
    Main service for mapping INCI names to comprehensive chemical identifiers.
    Always collects data from ALL available sources.
    """
    
    def __init__(self):
        # Domain-specific scraper configurations
        self.basic_scrapers = [
            ("pubchem", PubChemScraper)
        ]
        
        self.toxicology_scrapers = [ # TODO
            # ("comptox", CompToxScraper)  # Will be added
        ]
        
        self.regulatory_scrapers = [ # TODO
            # ("echa", ECHAScraper)  # Will be added
        ]
        
        self.physical_scrapers = [
            # TODO 
        ]
    
    async def map_ingredient(self, inci_name: str) -> ChemicalIdentityResult:
        """
        Map INCI ingredient to comprehensive chemical data from ALL sources.
        
        Args:
            inci_name: INCI name to map
            
        Returns:
            ChemicalIdentityResult with comprehensive data
        """
        start_time = time.time()
        
        basic_task = self._collect_basic_identifiers(inci_name)
        await asyncio.sleep(0.1)
        toxicology_task = self._collect_toxicology_data(inci_name)
        await asyncio.sleep(0.1)
        regulatory_task = self._collect_regulatory_data(inci_name)
        await asyncio.sleep(0.1) # check if we can remove this to avoid err 503
        physical_task = self._collect_physical_data(inci_name)
        
        try:
            basic_data, tox_data, reg_data, phys_data = await asyncio.gather(
                basic_task, toxicology_task, regulatory_task, physical_task,
                return_exceptions=True
            )
            
            errors = []
            if isinstance(basic_data, Exception):
                logger.warning(f"Basic identifiers error for {inci_name}: {basic_data}")
                errors.append(f"basic: {str(basic_data)}")
                basic_data = None
            if isinstance(tox_data, Exception):
                logger.warning(f"Toxicology data error for {inci_name}: {tox_data}")
                errors.append(f"toxicology: {str(tox_data)}")
                tox_data = None
            if isinstance(reg_data, Exception):
                logger.warning(f"Regulatory data error for {inci_name}: {reg_data}")
                errors.append(f"regulatory: {str(reg_data)}")
                reg_data = None
            if isinstance(phys_data, Exception):
                logger.warning(f"Physical data error for {inci_name}: {phys_data}")
                errors.append(f"physical: {str(phys_data)}")
                phys_data = None
            
            comprehensive_data = ComprehensiveChemicalData(
                inci_name=inci_name,
                basic_identifiers=basic_data,
                toxicology=tox_data,
                regulatory=reg_data,
                physical_chemical=phys_data
            )
            
            sources_used = []
            if basic_data:
                sources_used.append(basic_data.source)
            if tox_data:
                sources_used.append(tox_data.source)
            if reg_data:
                sources_used.append(reg_data.source)
            if phys_data:
                sources_used.append(phys_data.source)
                
            comprehensive_data.sources_used = list(set(sources_used))
            comprehensive_data.calculate_completeness()
            
            processing_time = (time.time() - start_time) * 1000
            
            return ChemicalIdentityResult(
                inci_name=inci_name,
                comprehensive_data=comprehensive_data,
                sources_checked=comprehensive_data.sources_used,
                errors=errors,
                found=len(sources_used) > 0,
                processing_time_ms=processing_time
            )
            
        except Exception as e:
            logger.error(f"Comprehensive mapping failed for {inci_name}: {e}")
            return ChemicalIdentityResult(
                inci_name=inci_name,
                found=False,
                errors=[str(e)],
                processing_time_ms=(time.time() - start_time) * 1000
            )
    
    async def _collect_basic_identifiers(self, inci_name: str) -> Optional[BasicChemicalIdentifiers]:
        """Collect basic chemical identifiers from primary sources."""
        for source_name, scraper_class in self.basic_scrapers:
            try:
                async with scraper_class() as scraper:
                    data = await scraper.search_by_name(inci_name)
                    
                    if data.get("found"):
                        return BasicChemicalIdentifiers(
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
            except Exception as e:
                logger.warning(f"Basic identifiers failed for {source_name}: {e}")
                continue
        
        return None
    
    async def _collect_toxicology_data(self, inci_name: str) -> Optional[ToxicologyData]:
        """Collect toxicological data from specialized sources."""
        if not self.toxicology_scrapers:
            return None
            
        basic_data = await self._collect_basic_identifiers(inci_name)
        cas_number = basic_data.cas_number if basic_data else None
        
        for source_name, scraper_class in self.toxicology_scrapers:
            try:
                async with scraper_class() as scraper:
                    if cas_number:
                        data = await scraper.search_by_cas(cas_number)
                    else:
                        data = await scraper.search_by_name(inci_name)
                    
                    if data.get("found"):
                        return ToxicologyData(
                            allergen_status=data.get("allergen_status"),
                            phototoxicity_risk=data.get("phototoxicity_risk"),
                            irritation_potential=data.get("irritation_potential"),
                            sensitization_risk=data.get("sensitization_risk"),
                            noael_value=data.get("noael_value"),
                            safe_concentration=data.get("safe_concentration"),
                            dermal_absorption=data.get("dermal_absorption"),
                            source=source_name,
                            confidence_score=data.get("confidence_score", 0.5)
                        )
            except Exception as e:
                logger.warning(f"Toxicology data failed for {source_name}: {e}")
                continue
        
        return None
    
    async def _collect_regulatory_data(self, inci_name: str) -> Optional[RegulatoryData]:
        """Collect regulatory data from compliance sources."""
        if not self.regulatory_scrapers:
            return None
            
        for source_name, scraper_class in self.regulatory_scrapers:
            try:
                async with scraper_class() as scraper:
                    data = await scraper.search_by_name(inci_name)
                    
                    if data.get("found"):
                        return RegulatoryData(
                            eu_restrictions=data.get("eu_restrictions"),
                            us_restrictions=data.get("us_restrictions"),
                            prohibited_categories=data.get("prohibited_categories"),
                            concentration_limits=data.get("concentration_limits"),
                            labeling_requirements=data.get("labeling_requirements"),
                            allergen_declaration_required=data.get("allergen_declaration_required"),
                            source=source_name,
                            confidence_score=data.get("confidence_score", 0.5)
                        )
            except Exception as e:
                logger.warning(f"Regulatory data failed for {source_name}: {e}")
                continue
        
        return None
    
    async def _collect_physical_data(self, inci_name: str) -> Optional[PhysicalChemicalData]:
        """Collect physical and chemical properties."""
        for source_name, scraper_class in self.physical_scrapers:
            try:
                async with scraper_class() as scraper:
                    data = await scraper.search_by_name(inci_name)
                    
                    if data.get("found"):
                        return PhysicalChemicalData(
                            solubility_water=data.get("solubility_water"),
                            solubility_oil=data.get("solubility_oil"),
                            ph_value=data.get("ph_value"),
                            logp_value=data.get("logp_value"),
                            stability=data.get("stability"),
                            volatility=data.get("volatility"),
                            melting_point=data.get("melting_point"),
                            source=source_name,
                            confidence_score=data.get("confidence_score", 0.5)
                        )
            except Exception as e:
                logger.warning(f"Physical data failed for {source_name}: {e}")
                continue
        
        return None
    
    async def map_ingredients_batch(self, inci_names: List[str]) -> List[ChemicalIdentityResult]:
        """
        Map multiple ingredients with comprehensive data collection.
        
        Args:
            inci_names: List of INCI names to map
            
        Returns:
            List of comprehensive mapping results
        """
        batch_size = 3
        results = []
        
        for i in range(0, len(inci_names), batch_size):
            batch = inci_names[i:i + batch_size]
            batch_tasks = [self.map_ingredient(name) for name in batch]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    error_result = ChemicalIdentityResult(
                        inci_name="unknown",
                        found=False,
                        errors=[str(result)]
                    )
                    results.append(error_result)
                else:
                    results.append(result)
            
            if i + batch_size < len(inci_names):
                await asyncio.sleep(2.0)
        
        return results
    
    @property
    def identifiers(self) -> Optional[BasicChemicalIdentifiers]:
        """Backward compatibility property for old API."""
        pass