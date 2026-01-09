from typing import List, Optional, Dict
from pydantic import BaseModel

class UserIn(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    email: str


class UserProfileIn(BaseModel):
    # Physiological data
    age: Optional[int] = None
    gender: Optional[str] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    
    # Skin type
    skinType: Optional[str] = None
    sensitiveSkin: Optional[bool] = None
    atopicSkin: Optional[bool] = None
    acneProne: Optional[bool] = None
    
    # Allergies (existing)
    hasAllergies: Optional[bool] = None
    cosmeticAllergies: Optional[List[str]] = None
    generalAllergies: Optional[List[str]] = None
    
    # Dermatological conditions (existing)
    acneVulgaris: Optional[bool] = None
    psoriasis: Optional[bool] = None
    eczema: Optional[bool] = None
    rosacea: Optional[bool] = None
    
    # Additional skin conditions
    barrierDysfunction: Optional[bool] = None
    seborrheicDermatitis: Optional[bool] = None
    periorbitalDermatitis: Optional[bool] = None
    contactDermatitis: Optional[bool] = None
    keratinizationDisorders: Optional[bool] = None
    
    # Medications (detailed - replacing bool with lists/strings)
    photosensitizingMedications: Optional[List[str]] = None
    diureticMedications: Optional[List[str]] = None
    retinoidTherapy: Optional[bool] = None
    corticosteroidUse: Optional[str] = None  # "topical", "systemic", "both", None
    immunosuppressants: Optional[List[str]] = None
    hormonalTherapy: Optional[str] = None  # "birth_control", "hrt", "other"
    otherMedications: Optional[str] = None
    medicalProcedures: Optional[str] = None
    
    # Legacy medication fields (kept for backward compatibility)
    photosensitizingDrugs: Optional[bool] = None
    diuretics: Optional[bool] = None
    
    # Lifestyle
    smoking: Optional[str] = None
    stressLevel: Optional[int] = None
    tanning: Optional[str] = None
    pregnancy: Optional[bool] = None
    
    # Cosmetic exposure patterns (for HED calculations)
    productUsageFrequency: Optional[str] = None  # "daily", "weekly", "occasionally"
    typicalApplicationAreas: Optional[List[str]] = None  # ["face", "body", "hands", "neck"]
    bodyBackgroundExposure: Optional[float] = None  # BSA in m²
    preferredProductTypes: Optional[List[str]] = None  # ["leave-on", "rinse-off", "both"]
    
    # Ingredient safety history (blacklist)
    knownIntolerances: Optional[List[str]] = None  # ["fragrance", "methylisothiazolinone"]
    previousAdverseReactions: Optional[List[Dict]] = None  # [{"ingredient": "SLS", "reaction": "irritation", "severity": "moderate"}]
    dermatologistRecommendedAvoid: Optional[List[str]] = None
    
    # User preferences
    preferNatural: Optional[bool] = None
    veganOnly: Optional[bool] = None
    fragranceFree: Optional[bool] = None
    avoidCategories: Optional[List[str]] = None  # ["parabens", "sulfates", "silicones"]
    certificationPreferences: Optional[List[str]] = None  # ["ecocert", "cosmos", "natrue"]
    
    # Environmental factors
    climateType: Optional[str] = None  # "dry", "humid", "temperate", "cold"
    pollutionExposure: Optional[str] = None  # "high", "moderate", "low"
    sunExposure: Optional[str] = None  # "high_outdoor", "moderate", "minimal_indoor"
    waterHardness: Optional[str] = None  # "hard", "soft", "moderate"
    
    # Cosmetic goals
    primaryConcerns: Optional[List[str]] = None  # ["anti_aging", "acne", "hydration", "brightening"]

class UserProfileOut(UserProfileIn):
    pass