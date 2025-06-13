from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from datetime import datetime


class BasicChemicalIdentifiers(BaseModel):
    """Core chemical idetifiers."""
    inci_name: str
    cas_number: Optional[str] = None
    ec_number: Optional[str] = None
    smiles: Optional[str] = None
    inchi: Optional[str] = None
    inchi_key: Optional[str] = None
    systematic_name: Optional[str] = None
    molecular_formula: Optional[str] = None
    molecular_weight: Optional[float] = None
    
    source: str
    confidence_score: float = 0.0


class ToxicologyData(BaseModel):
    """Toxicological and safety data."""
    allergen_status: Optional[str] = None
    photoxicity_rist: Optional[str] = None
    irritation_potential: Optional[str] = None
    sensitization_risk: Optional[str] = None
    noael_value: Optional[float] = None
    safe_concentration: Optional[float] = None
    dermal_absorption: Optional[float] = None
    
    source: str
    confidence_score: float = 0.0  
    
    
class RegulatoryData(BaseModel):
    """Regulatory restrictions and compliance data."""
    eu_restrictions: Optional[List[str]] = None
    us_restrictions: Optional[List[str]] = None
    prohibited_categories: Optional[List[str]] = None
    concentration_limits: Optional[Dict[str, float]] = None
    labeling_requirements: Optional[List[str]] = None
    allergen_declaration_required: Optional[bool] = None

    source: str
    confidence_score: float = 0.0


class PhysicalChemicalData(BaseModel):
    """Physical and chemical properties."""
    solubility_water: Optional[str] = None
    solubility_oil: Optional[str] = None
    ph_value: Optional[float] = None
    logp_value: Optional[float] = None
    stability: Optional[str] = None
    volatility: Optional[str] = None
    melting_point: Optional[float] = None
    source: str
    confidence_score: float = 0.0


class ComprehensiveChemicalData(BaseModel):
    """Complete aggregated chemical data from all sources."""
    inci_name: str
    basic_identifiers: Optional[BasicChemicalIdentifiers] = None
    toxicology: Optional[ToxicologyData] = None
    regulatory: Optional[RegulatoryData] = None
    physical_chemical: Optional[PhysicalChemicalData] = None
    
    sources_used: List[str] = []
    data_completeness: float = 0.0
    total_confidence: float = 0.0
    last_updated: datetime = Field(default_factory=datetime.now)
    
    def calculate_completeness(self):
        """Calculate data completeness percentage."""
        domains = [
            self.basic_identifiers,
            self.toxicology, 
            self.regulatory,
            self.physical_chemical
        ]
        filled_domains = sum(1 for domain in domains if domain is not None)
        self.data_completeness = (filled_domains / len(domains)) * 100
        
        confidences = []
        if self.basic_identifiers:
            confidences.append(self.basic_identifiers.confidence_score)
        if self.toxicology:
            confidences.append(self.toxicology.confidence_score)
        if self.regulatory:
            confidences.append(self.regulatory.confidence_score)
        if self.physical_chemical:
            confidences.append(self.physical_chemical.confidence_score)
            
        self.total_confidence = sum(confidences) / len(confidences) if confidences else 0.0


class ChemicalIdentityResult(BaseModel):
    """Enhanced result with comprehensive data."""
    inci_name: str
    comprehensive_data: Optional[ComprehensiveChemicalData] = None
    sources_checked: List[str] = []
    errors: List[str] = []
    found: bool = False
    processing_time_ms: float = 0.0
    
    @property
    def identifiers(self) -> Optional[BasicChemicalIdentifiers]:
        """Backward compatibility property."""
        return self.comprehensive_data.basic_identifiers if self.comprehensive_data else None


ChemicalIdentifiers = BasicChemicalIdentifiers