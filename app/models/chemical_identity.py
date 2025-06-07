from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime

class ChemicalIdentifiers(BaseModel):
    """Model for storign chemical identifiers of an ingredient."""
    
    inci_name: str
    cas_number: Optional[str] = None
    ec_number: Optional[str] = None
    smiles: Optional[str] = None
    inchi: Optional[str] = None
    inchi_key: Optional[str] = None
    systematic_name: Optional[str] = None
    
    # Metadata
    source: str
    confidence_score: float = 0.0
    last_updated: datetime = datetime.now()
    
class ChemicalIdentityResult(BaseModel):
    """Result of chemical identity mapping process."""
    
    inci_name: str
    identifiers: Optional[ChemicalIdentifiers] = None
    sources_cheked: List[str] = []
    errors: List[str] = []
    found: bool = False
    processing_time_ms: float = 0.0
    