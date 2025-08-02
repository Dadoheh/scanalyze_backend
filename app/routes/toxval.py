from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List

from ..core.mysql_database import get_db
from ..core.auth import get_current_user
from ..service.toxval_service import ToxValService

router = APIRouter(prefix="/toxval", tags=["toxval"])
toxval_service = ToxValService()

@router.get("/{cas_number}", response_model=Dict[str, Any])
async def get_toxval_data(
    cas_number: str, 
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Retrieve toxicological data for a component from the ToxVal database by CAS number."""
    result = await toxval_service.get_complete_toxval_data(db, cas_number)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.get("/skin-eye/{dtxsid}", response_model=List[Dict[str, Any]])
async def get_skin_eye_data(
    dtxsid: str, 
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Retrieve data on skin and eye effects for a given DTXSID."""
    result = await toxval_service.get_skin_eye_data(db, dtxsid)
    return result

@router.get("/cancer/{dtxsid}", response_model=List[Dict[str, Any]])
async def get_cancer_data(
    dtxsid: str, 
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Retrieve data on carcinogenic potential for a given DTXSID."""
    result = await toxval_service.get_cancer_data(db, dtxsid)
    return result

@router.get("/search", response_model=List[Dict[str, Any]])
async def search_ingredients(
    term: str = Query(..., description="Search term (name or CAS number)"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Search for ingredients by name or CAS number."""
    result = await toxval_service.search_ingredients(db, term)
    return result
