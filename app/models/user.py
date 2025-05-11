from typing import List, Optional
from pydantic import BaseModel

class UserIn(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    email: str


class UserProfileIn(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    
    skinType: Optional[str] = None
    sensitiveSkin: Optional[bool] = None
    atopicSkin: Optional[bool] = None
    acneProne: Optional[bool] = None
    
    hasAllergies: Optional[bool] = None
    cosmeticAllergies: Optional[List[str]] = None
    generalAllergies: Optional[List[str]] = None
    
    acneVulgaris: Optional[bool] = None
    psoriasis: Optional[bool] = None
    eczema: Optional[bool] = None
    rosacea: Optional[bool] = None
    
    photosensitizingDrugs: Optional[bool] = None
    diuretics: Optional[bool] = None
    otherMedications: Optional[str] = None
    medicalProcedures: Optional[str] = None
    
    smoking: Optional[bool] = None
    stressLevel: Optional[str] = None
    tanning: Optional[bool] = None

class UserProfileOut(UserProfileIn):
    pass