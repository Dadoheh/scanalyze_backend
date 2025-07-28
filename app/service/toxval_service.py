from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.sql import text
from typing import Optional, List, Dict, Any
from ..models.toxval_models import Chemical, Toxval, MvSkinEye, MvCancerSummary, Species

class ToxValService:
    """Service for retrieving data from the ToxVal database."""
    
    async def find_chemical_by_cas(self, db: AsyncSession, cas_number: str) -> Optional[Dict]:
        """Search for a chemical by CAS number."""
        query = select(Chemical).where(Chemical.casrn == cas_number)
        result = await db.execute(query)
        chemical = result.scalars().first()
        
        if chemical:
            return {
                "dtxsid": chemical.dtxsid,
                "casrn": chemical.casrn,
                "name": chemical.name
            }
        return None
    
    async def find_chemical_by_name(self, db: AsyncSession, name: str) -> Optional[Dict]:
        """Search for a chemical by name (or part of it)."""
        query = select(Chemical).where(Chemical.name.like(f"%{name}%"))
        result = await db.execute(query)
        chemicals = result.scalars().all()
        
        return [{"dtxsid": c.dtxsid, "casrn": c.casrn, "name": c.name} for c in chemicals]
    
    async def get_skin_eye_data(self, db: AsyncSession, dtxsid: str) -> List[Dict]:
        """Retrieve data on skin and eye effects for a chemical."""
        query = select(MvSkinEye).where(MvSkinEye.dtxsid == dtxsid)
        result = await db.execute(query)
        data = result.scalars().all()
        
        return [
            {
                "endpoint": item.endpoint,
                "classification": item.classification,
                "result_text": item.result_text,
                "score": item.score,
                "species": item.species,
                "source": item.source
            } 
            for item in data
        ]
    
    async def get_cancer_data(self, db: AsyncSession, dtxsid: str) -> List[Dict]:
        """Retrieve data on the carcinogenic potential of a chemical."""
        query = select(MvCancerSummary).where(MvCancerSummary.dtxsid == dtxsid)
        result = await db.execute(query)
        data = result.scalars().all()
        
        return [
            {
                "source": item.source,
                "exposure_route": item.exposure_route,
                "cancer_call": item.cancer_call,
                "source_url": item.source_url
            } 
            for item in data
        ]
    
    async def get_dermal_toxicity(self, db: AsyncSession, dtxsid: str) -> List[Dict]:
        """Retrieve data on dermal toxicity."""
        query = select(Toxval).where(
            Toxval.dtxsid == dtxsid,
            or_(Toxval.exposure_route.like('%Dermal%'), 
                Toxval.exposure_route.like('%Cutaneous%'),
                Toxval.exposure_route_original.like('%Dermal%'),
                Toxval.exposure_route_original.like('%Cutaneous%'))
        )
        result = await db.execute(query)
        data = result.scalars().all()
        
        return [
            {
                "toxval_type": item.toxval_type,
                "toxval_numeric": item.toxval_numeric,
                "toxval_units": item.toxval_units,
                "toxicological_effect": item.toxicological_effect,
                "exposure_route": item.exposure_route,
                "species": item.species_original,
                "source": item.source
            }
            for item in data
        ]
    
    async def get_complete_toxval_data(self, db: AsyncSession, cas_number: str) -> Dict[str, Any]:
        """Retrieve all toxicological data for a chemical by CAS number."""
        chemical = await self.find_chemical_by_cas(db, cas_number)
        if not chemical:
            return {"error": "Chemical not found in the ToxVal database"}
        
        dtxsid = chemical["dtxsid"]
        
        return {
            "chemical_info": chemical,
            "skin_eye_data": await self.get_skin_eye_data(db, dtxsid),
            "cancer_data": await self.get_cancer_data(db, dtxsid),
            "dermal_toxicity": await self.get_dermal_toxicity(db, dtxsid)
        }

    async def search_ingredients(self, db: AsyncSession, search_term: str) -> List[Dict]:
        """Search for chemicals by name or CAS number."""
        # Check if search_term looks like a CAS number (contains hyphens)
        if "-" in search_term:
            # Search exactly by CAS
            query = select(Chemical).where(Chemical.casrn == search_term)
        else:
            # Search by name using LIKE
            query = select(Chemical).where(Chemical.name.like(f"%{search_term}%"))
        
        result = await db.execute(query)
        chemicals = result.scalars().all()
        
        return [{"dtxsid": c.dtxsid, "casrn": c.casrn, "name": c.name} for c in chemicals]