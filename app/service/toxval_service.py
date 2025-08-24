from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.sql import text
from typing import Optional, List, Dict, Any
import logging
from ..models.toxval_models import Chemical, MvToxValDB, Toxval, MvSkinEye, MvCancerSummary, Species

logger = logging.getLogger(__name__)

class ToxValService:
    """Service for retrieving data from the ToxVal database."""
    
    async def find_chemical_by_cas(self, db: AsyncSession, cas_number: str) -> Optional[Dict]:
        """Wyszukiwanie składnika po numerze CAS."""
        logger.info(f"Searching ToxVal for CAS: {cas_number}")
        query = select(Chemical).where(Chemical.casrn == cas_number)
        result = await db.execute(query)
        chemical = result.scalars().first()
        
        if chemical:
            logger.info(f"Found chemical in ToxVal: {chemical.dtxsid} - {chemical.name}")
            return {
                "dtxsid": chemical.dtxsid,
                "casrn": chemical.casrn,
                "name": chemical.name
            }
        logger.warning(f"No chemical found in ToxVal for CAS: {cas_number}")
        return None
    
    async def get_skin_eye_data(self, db: AsyncSession, dtxsid: str) -> List[Dict]:
        """Pobierz dane o działaniu na skórę i oczy dla składnika."""
        logger.info(f"Fetching skin/eye data for DTXSID: {dtxsid}")
        query = select(MvSkinEye).where(MvSkinEye.dtxsid == dtxsid)
        result = await db.execute(query)
        data = result.scalars().all()
        
        skin_eye_data = [
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
        
        logger.info(f"Found {len(skin_eye_data)} skin/eye records for {dtxsid}")
        logger.debug(f"Skin/eye data: {skin_eye_data[:5]}{'...' if len(skin_eye_data) > 5 else ''}")
        return skin_eye_data
    
    async def get_cancer_data(self, db: AsyncSession, dtxsid: str) -> List[Dict]:
        """Pobierz dane o potencjale rakotwórczym składnika."""
        logger.info(f"Fetching cancer data for DTXSID: {dtxsid}")
        query = select(MvCancerSummary).where(MvCancerSummary.dtxsid == dtxsid)
        result = await db.execute(query)
        data = result.scalars().all()
        
        cancer_data = [
            {
                "source": item.source,
                "exposure_route": item.exposure_route,
                "cancer_call": item.cancer_call,
                "source_url": item.source_url
            } 
            for item in data
        ]
        
        logger.info(f"Found {len(cancer_data)} cancer records for {dtxsid}")
        logger.debug(f"Cancer data: {cancer_data}")
        return cancer_data
    
    async def get_dermal_toxicity(self, db: AsyncSession, dtxsid: str) -> List[Dict]:
        """Pobierz dane o toksyczności skórnej."""
        logger.info(f"Fetching dermal toxicity for DTXSID: {dtxsid}")
        query = select(Toxval).where(
            Toxval.dtxsid == dtxsid,
            or_(Toxval.exposure_route.like('%Dermal%'), 
                Toxval.exposure_route.like('%Cutaneous%'),
                Toxval.exposure_route_original.like('%Dermal%'),
                Toxval.exposure_route_original.like('%Cutaneous%'))
        )
        result = await db.execute(query)
        data = result.scalars().all()
        
        toxicity_data = [
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
        
        logger.info(f"Found {len(toxicity_data)} dermal toxicity records for {dtxsid}")
        logger.debug(f"Sample toxicity data: {toxicity_data} .end.")
        return toxicity_data
    
    async def get_toxvaldb_data(self, db: AsyncSession, dtxsid: str = None, casrn: str = None) -> List[Dict]:
        """Data from materialized view ToxValDB."""
        logger.info(f"Fetching ToxValDB data for DTXSID: {dtxsid} or CAS: {casrn}")
        
        if dtxsid:
            query = select(MvToxValDB).where(MvToxValDB.dtxsid == dtxsid)
        elif casrn:
            query = select(MvToxValDB).where(MvToxValDB.casrn == casrn)
        else:
            return []
        
        result = await db.execute(query)
        data = result.scalars().all()
        
        toxval_data = [
            {
                "toxval_type": item.toxval_type,
                "toxval_numeric": item.toxval_numeric,
                "toxval_units": item.toxval_units,
                "risk_assessment_class": item.risk_assessment_class,
                "human_eco": item.human_eco,
                "study_type": item.study_type,
                "species_common": item.species_common,
                "exposure_route": item.exposure_route,
                "toxicological_effect": item.toxicological_effect,
                "source": item.source,
                "qc_category": item.qc_category
            }
            for item in data
        ]
        
        logger.info(f"Found {len(toxval_data)} ToxValDB records")
        logger.debug(f"Sample ToxValDB data: {toxval_data}")
        return toxval_data

    async def get_complete_toxval_data(self, db: AsyncSession, cas_number: str) -> Dict[str, Any]:
        """Pobierz wszystkie dane toksykologiczne dla składnika po CAS."""
        logger.info(f"Getting complete ToxVal data for CAS: {cas_number}")
        chemical = await self.find_chemical_by_cas(db, cas_number)
        if not chemical:
            logger.warning(f"No chemical found in ToxVal database for CAS: {cas_number}")
            return {"error": "Składnik nie znaleziony w bazie ToxVal"}
        
        dtxsid = chemical["dtxsid"]
        
        skin_eye_data = await self.get_skin_eye_data(db, dtxsid)
        cancer_data = await self.get_cancer_data(db, dtxsid)
        dermal_toxicity = await self.get_dermal_toxicity(db, dtxsid)
        
        result = {
            "chemical_info": chemical,
            "skin_eye_data": skin_eye_data,
            "cancer_data": cancer_data,
            "dermal_toxicity": dermal_toxicity
        }
        
        logger.info(f"Complete ToxVal data summary for {chemical['name']} ({cas_number}):")
        logger.info(f"  - Skin/eye records: {len(skin_eye_data)}")
        logger.info(f"  - Cancer records: {len(cancer_data)}")
        logger.info(f"  - Dermal toxicity records: {len(dermal_toxicity)}")
        
        return result
    