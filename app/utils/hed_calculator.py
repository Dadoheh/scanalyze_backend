"""
HED Calculator - Human Equivalent Dose Conversion
Based on: Nair & Jacob (2016) "A simple practice guide for dose conversion between animals and human"

This module implements allometric scaling formulas for converting toxicological doses
between animal species and humans using body surface area (BSA) normalization.

Key Concepts:
- NOAEL: No Observed Adverse Effect Level
- HED: Human Equivalent Dose
- AED: Animal Equivalent Dose
- MRSD: Maximum Recommended Starting Dose
- Km: Conversion coefficient based on body surface area
"""

from typing import Optional, Dict, Literal
from enum import Enum


class Species(str, Enum):
    """Animal species with their standard Km factors from FDA guidance."""
    MOUSE = "mouse"
    HAMSTER = "hamster"
    RAT = "rat"
    FERRET = "ferret"
    GUINEA_PIG = "guinea_pig"
    RABBIT = "rabbit"
    DOG = "dog"
    MONKEY_RHESUS = "monkey_rhesus"
    MARMOSET = "marmoset"
    SQUIRREL_MONKEY = "squirrel_monkey"
    BABOON = "baboon"
    MICRO_PIG = "micro_pig"
    MINI_PIG = "mini_pig"
    HUMAN = "human"


# Km factors from FDA guidance (Table from Nair & Jacob 2016, Section 4)
KM_FACTORS: Dict[Species, float] = {
    Species.HUMAN: 37.0,
    Species.MOUSE: 3.0,
    Species.HAMSTER: 5.0,
    Species.RAT: 6.0,
    Species.FERRET: 7.0,
    Species.GUINEA_PIG: 8.0,
    Species.RABBIT: 12.0,
    Species.DOG: 20.0,
    Species.MONKEY_RHESUS: 12.0,
    Species.MARMOSET: 6.0,
    Species.SQUIRREL_MONKEY: 7.0,
    Species.BABOON: 20.0,
    Species.MICRO_PIG: 27.0,
    Species.MINI_PIG: 35.0,
}

# Standard body weights (kg) for common species
STANDARD_WEIGHTS: Dict[Species, float] = {
    Species.HUMAN: 60.0,
    Species.MOUSE: 0.020,  # 20g
    Species.RAT: 0.150,    # 150g
    Species.RABBIT: 1.8,
    Species.DOG: 10.0,
    Species.MONKEY_RHESUS: 3.0,
}


class HEDCalculator:
    """
    Calculator for Human Equivalent Dose (HED) conversions.
    
    Implements multiple methods from Nair & Jacob (2016):
    - Eq. 1: Weight-based HED calculation
    - Eq. 2/3: Km-based HED calculation
    - Eq. 4: Unit conversion (mg/kg ↔ mg/m²)
    - Eq. 5: Animal Equivalent Dose (AED)
    - MRSD: Maximum Recommended Starting Dose calculation
    """
    
    def __init__(self, human_weight_kg: float = 60.0):
        """
        Initialize HED calculator.
        
        Args:
            human_weight_kg: Reference human body weight in kg (default: 60 kg)
        """
        self.human_weight = human_weight_kg
        self.km_human = KM_FACTORS[Species.HUMAN]
    
    def calculate_hed_by_weight(
        self,
        animal_dose_mg_kg: float,
        animal_weight_kg: float,
        human_weight_kg: Optional[float] = None
    ) -> float:
        """
        Calculate HED using Equation 1 (weight-based allometric scaling).
        
        Eq. 1: HED (mg/kg) = Animal NOAEL (mg/kg) × (W_animal / W_human)^0.33
        
        Example from paper (Section 5.1):
            NOAEL (rat) = 18 mg/kg, W_rat = 0.15 kg, W_human = 60 kg
            HED = 18 × (0.15/60)^0.33 = 18 × 0.14 = 2.5 mg/kg
        
        Args:
            animal_dose_mg_kg: Animal dose in mg/kg (e.g., NOAEL)
            animal_weight_kg: Animal body weight in kg
            human_weight_kg: Human body weight in kg (default: 60 kg)
        
        Returns:
            HED in mg/kg
        """
        if human_weight_kg is None:
            human_weight_kg = self.human_weight
        
        # Eq. 1: HED = Animal dose × (W_animal / W_human)^0.33
        weight_ratio = animal_weight_kg / human_weight_kg
        hed_mg_kg = animal_dose_mg_kg * (weight_ratio ** 0.33)
        
        return hed_mg_kg
    
    def calculate_hed_by_km(
        self,
        animal_dose_mg_kg: float,
        animal_species: Species,
        custom_km_animal: Optional[float] = None
    ) -> float:
        """
        Calculate HED using Equation 2 (Km-based conversion).
        
        Eq. 2: HED (mg/kg) = Animal dose (mg/kg) × (Km_animal / Km_human)
        Eq. 3: HED (mg/kg) = Animal dose (mg/kg) × K-ratio
               where K-ratio = Km_animal / Km_human
        
        Example from paper (Section 5.2):
            NOAEL (rat) = 50 mg/kg, Km_rat = 6, Km_human = 37
            HED = 50 × (6/37) = 50 × 0.162 = 8.1 mg/kg
        
        Args:
            animal_dose_mg_kg: Animal dose in mg/kg
            animal_species: Species enum
            custom_km_animal: Optional custom Km value (for weight variations)
        
        Returns:
            HED in mg/kg
        """
        km_animal = custom_km_animal if custom_km_animal else KM_FACTORS[animal_species]
        
        # Eq. 2: HED = Animal dose × (Km_animal / Km_human)
        k_ratio = km_animal / self.km_human
        hed_mg_kg = animal_dose_mg_kg * k_ratio
        
        return hed_mg_kg
    
    def calculate_aed(
        self,
        human_dose_mg_kg: float,
        animal_species: Species,
        custom_km_animal: Optional[float] = None
    ) -> float:
        """
        Calculate Animal Equivalent Dose (AED) using Equation 5.
        
        Eq. 5: AED (mg/kg) = Human dose (mg/kg) × (Km_human / Km_animal)
        
        Example from paper (Section 5.5):
            Human dose = 10 mg/kg, Km_human = 37, Km_rat = 6
            AED = 10 × (37/6) = 10 × 6.17 = 61.7 mg/kg
        
        Args:
            human_dose_mg_kg: Human dose in mg/kg
            animal_species: Target animal species
            custom_km_animal: Optional custom Km value
        
        Returns:
            AED in mg/kg for the target animal species
        """
        km_animal = custom_km_animal if custom_km_animal else KM_FACTORS[animal_species]
        
        # Eq. 5: AED = Human dose × (Km_human / Km_animal)
        aed_mg_kg = human_dose_mg_kg * (self.km_human / km_animal)
        
        return aed_mg_kg
    
    def convert_mg_kg_to_mg_m2(
        self,
        dose_mg_kg: float,
        species: Species,
        custom_km: Optional[float] = None
    ) -> float:
        """
        Convert dose from mg/kg to mg/m² using Equation 4.
        
        Eq. 4: dose (mg/m²) = Km × dose (mg/kg)
        
        Args:
            dose_mg_kg: Dose in mg/kg
            species: Species for Km factor
            custom_km: Optional custom Km value
        
        Returns:
            Dose in mg/m²
        """
        km = custom_km if custom_km else KM_FACTORS[species]
        return km * dose_mg_kg
    
    def convert_mg_m2_to_mg_kg(
        self,
        dose_mg_m2: float,
        species: Species,
        custom_km: Optional[float] = None
    ) -> float:
        """
        Convert dose from mg/m² to mg/kg using Equation 4.
        
        Eq. 4: dose (mg/kg) = dose (mg/m²) / Km
        
        Args:
            dose_mg_m2: Dose in mg/m²
            species: Species for Km factor
            custom_km: Optional custom Km value
        
        Returns:
            Dose in mg/kg
        """
        km = custom_km if custom_km else KM_FACTORS[species]
        return dose_mg_m2 / km
    
    def calculate_km_for_weight(
        self,
        animal_weight_kg: float,
        reference_species: Species
    ) -> float:
        """
        Calculate Km for a specific animal weight using allometric scaling.
        
        From Section 6: Km varies with body weight according to W^(2/3)
        
        Example from paper (Section 6):
            Rat 100g → Km = 5.2
            Rat 150g → Km = 6.0
            Rat 250g → Km = 7.0
        
        Args:
            animal_weight_kg: Actual animal weight in kg
            reference_species: Species for baseline Km
        
        Returns:
            Adjusted Km factor
        """
        # Get reference weight and Km
        if reference_species not in STANDARD_WEIGHTS:
            raise ValueError(f"No standard weight defined for {reference_species}")
        
        reference_weight = STANDARD_WEIGHTS[reference_species]
        reference_km = KM_FACTORS[reference_species]
        
        # Km scales with W^(2/3)
        weight_ratio = animal_weight_kg / reference_weight
        adjusted_km = reference_km * (weight_ratio ** (2/3))
        
        return adjusted_km
    
    def calculate_mrsd(
        self,
        noael_values: Dict[Species, float],
        safety_factor: float = 10.0,
        human_weight_kg: Optional[float] = None,
        method: Literal["weight", "km"] = "km"
    ) -> Dict[str, float]:
        """
        Calculate Maximum Recommended Starting Dose (MRSD) using 5-step procedure.
        
        From Section 7 - MRSD Procedure:
        1. Determine NOAEL for each species
        2. Convert NOAEL to HED (using Eq. 1 or Eq. 2/3)
        3. Select most sensitive species (lowest HED)
        4. Apply safety factor (typically 10)
        5. Convert MRSD to total dose
        
        Example from paper (Section 5.1):
            NOAEL (rat) = 18 mg/kg → HED = 2.5 mg/kg
            Total dose = 2.5 × 60 kg = 150 mg
            MRSD = 150 / 10 = 15 mg
        
        Args:
            noael_values: Dictionary of {Species: NOAEL in mg/kg}
            safety_factor: Safety factor (default: 10)
            human_weight_kg: Human weight in kg
            method: "weight" for Eq. 1, "km" for Eq. 2/3
        
        Returns:
            Dictionary with MRSD calculations
        """
        if human_weight_kg is None:
            human_weight_kg = self.human_weight
        
        # Step 1 & 2: Calculate HED for each species
        hed_values = {}
        for species, noael in noael_values.items():
            if method == "weight":
                if species not in STANDARD_WEIGHTS:
                    continue
                animal_weight = STANDARD_WEIGHTS[species]
                hed = self.calculate_hed_by_weight(noael, animal_weight, human_weight_kg)
            else:  # km method
                hed = self.calculate_hed_by_km(noael, species)
            
            hed_values[species] = hed
        
        # Step 3: Select most sensitive species (lowest HED)
        most_sensitive_species = min(hed_values, key=hed_values.get)
        lowest_hed = hed_values[most_sensitive_species]
        
        # Step 4: Apply safety factor
        mrsd_mg_kg = lowest_hed / safety_factor
        
        # Step 5: Calculate total dose
        total_mrsd_mg = mrsd_mg_kg * human_weight_kg
        
        return {
            "hed_values": hed_values,
            "most_sensitive_species": most_sensitive_species.value,
            "lowest_hed_mg_kg": lowest_hed,
            "safety_factor": safety_factor,
            "mrsd_mg_kg": mrsd_mg_kg,
            "total_mrsd_mg": total_mrsd_mg,
            "human_weight_kg": human_weight_kg
        }
    
    def calculate_injection_volume(
        self,
        dose_mg_kg: float,
        animal_weight_kg: float,
        concentration_mg_ml: float
    ) -> float:
        """
        Calculate injection volume for parenteral administration.
        
        From Section 8:
        Injection volume (mL) = (Animal weight (kg) × Dose (mg/kg)) / Concentration (mg/mL)
        
        Example from paper (Section 8):
            Concentration = 10 mg/mL, AED = 62 mg/kg, rat weight = 0.25 kg
            Volume = (0.25 × 62) / 10 = 1.55 mL
        
        Args:
            dose_mg_kg: Dose in mg/kg
            animal_weight_kg: Animal weight in kg
            concentration_mg_ml: Drug concentration in mg/mL
        
        Returns:
            Injection volume in mL
        """
        total_dose_mg = animal_weight_kg * dose_mg_kg
        volume_ml = total_dose_mg / concentration_mg_ml
        
        return volume_ml
    
    def get_limitations(self) -> Dict[str, list]:
        """
        Return method limitations from Section 9.
        
        Returns:
            Dictionary of limitations and contraindications
        """
        return {
            "do_not_use_for_human_scaling": [
                "Adult to pediatric dose conversion",
                "Geriatric dose adjustments"
            ],
            "do_not_use_for_routes": [
                "Topical administration",
                "Nasal administration",
                "Subcutaneous injection",
                "Intramuscular injection"
            ],
            "do_not_use_for_substances": [
                "Large proteins >100,000 Da (parenteral)"
            ],
            "warnings": [
                "Results are approximations",
                "Does not replace full PK/PD evaluation",
                "Species-specific toxicity may differ from allometric predictions"
            ]
        }
    
    def assess_dermal_safety(
        self,
        animal_dose_mg_kg: float,
        animal_species: Species,
        application_area_cm2: float = 100.0,
        skin_penetration_percent: float = 10.0,
        safety_factor: float = 100.0
    ) -> Dict[str, float]:
        """
        Assess dermal safety for cosmetic ingredient based on animal toxicology data.
        
        This is a specialized method for cosmetic safety assessment combining:
        - HED conversion
        - Dermal absorption estimation
        - Conservative safety factors
        
        Args:
            animal_dose_mg_kg: Animal NOAEL in mg/kg (e.g., from ToxVal)
            animal_species: Species from toxicology study
            application_area_cm2: Typical application area (default: 100 cm²)
            skin_penetration_percent: Estimated dermal penetration (default: 10%)
            safety_factor: Total safety factor (default: 100 for cosmetics)
        
        Returns:
            Dictionary with safety assessment results
        """
        # Calculate HED
        hed_mg_kg = self.calculate_hed_by_km(animal_dose_mg_kg, animal_species)
        
        # Total safe dose for 60 kg human
        safe_systemic_dose_mg = hed_mg_kg * self.human_weight
        
        # Apply safety factor
        safe_dose_with_sf_mg = safe_systemic_dose_mg / safety_factor
        
        # Account for dermal penetration
        # If only 10% penetrates, we can apply 10x more on skin
        penetration_factor = skin_penetration_percent / 100.0
        max_dermal_application_mg = safe_dose_with_sf_mg / penetration_factor
        
        # Calculate safe concentration (mg/cm²)
        safe_concentration_mg_cm2 = max_dermal_application_mg / application_area_cm2
        
        # Convert to common units (mg/g or % w/w assuming 1g/cm² density)
        safe_concentration_percent = (safe_concentration_mg_cm2 / 10.0)  # mg/cm² to %
        
        return {
            "animal_noael_mg_kg": animal_dose_mg_kg,
            "hed_mg_kg": hed_mg_kg,
            "safe_systemic_dose_mg": safe_systemic_dose_mg,
            "safety_factor": safety_factor,
            "safe_dose_with_sf_mg": safe_dose_with_sf_mg,
            "skin_penetration_percent": skin_penetration_percent,
            "max_dermal_application_mg": max_dermal_application_mg,
            "application_area_cm2": application_area_cm2,
            "safe_concentration_mg_cm2": safe_concentration_mg_cm2,
            "safe_concentration_percent": safe_concentration_percent,
            "assessment": "SAFE" if safe_concentration_percent > 0.01 else "REQUIRES_FURTHER_EVALUATION"
        }


# Example usage
if __name__ == "__main__":
    calculator = HEDCalculator(human_weight_kg=60.0)
    
    # Example 1: Weight-based HED (Section 5.1)
    print("=== Example 1: Weight-based HED (Eq. 1) ===")
    hed1 = calculator.calculate_hed_by_weight(
        animal_dose_mg_kg=18.0,
        animal_weight_kg=0.15  # 150g rat
    )
    print(f"Rat NOAEL: 18 mg/kg → HED: {hed1:.2f} mg/kg")
    print(f"Total dose for 60kg human: {hed1 * 60:.1f} mg")
    print(f"MRSD with SF=10: {(hed1 * 60) / 10:.1f} mg\n")
    
    # Example 2: Km-based HED (Section 5.2)
    print("=== Example 2: Km-based HED (Eq. 2) ===")
    hed2 = calculator.calculate_hed_by_km(
        animal_dose_mg_kg=50.0,
        animal_species=Species.RAT
    )
    print(f"Rat NOAEL: 50 mg/kg → HED: {hed2:.2f} mg/kg\n")
    
    # Example 3: AED calculation (Section 5.5)
    print("=== Example 3: AED (Eq. 5) ===")
    aed = calculator.calculate_aed(
        human_dose_mg_kg=10.0,
        animal_species=Species.RAT
    )
    print(f"Human dose: 10 mg/kg → Rat AED: {aed:.1f} mg/kg\n")
    
    # Example 4: Injection volume (Section 8)
    print("=== Example 4: Injection Volume ===")
    volume = calculator.calculate_injection_volume(
        dose_mg_kg=62.0,
        animal_weight_kg=0.25,  # 250g rat
        concentration_mg_ml=10.0
    )
    print(f"AED 62 mg/kg, 250g rat, 10mg/mL → {volume:.2f} mL\n")
    
    # Example 5: MRSD calculation (Section 7)
    print("=== Example 5: MRSD Procedure ===")
    mrsd_result = calculator.calculate_mrsd(
        noael_values={
            Species.RAT: 18.0,
            Species.MOUSE: 25.0,
            Species.RABBIT: 12.0
        },
        safety_factor=10.0,
        method="km"
    )
    print(f"Most sensitive species: {mrsd_result['most_sensitive_species']}")
    print(f"Lowest HED: {mrsd_result['lowest_hed_mg_kg']:.2f} mg/kg")
    print(f"MRSD: {mrsd_result['mrsd_mg_kg']:.2f} mg/kg")
    print(f"Total MRSD: {mrsd_result['total_mrsd_mg']:.1f} mg\n")
    
    # Example 6: Dermal safety assessment for cosmetics
    print("=== Example 6: Dermal Safety (Cosmetic Use) ===")
    safety = calculator.assess_dermal_safety(
        animal_dose_mg_kg=100.0,  # Rat NOAEL
        animal_species=Species.RAT,
        application_area_cm2=100.0,
        skin_penetration_percent=10.0,
        safety_factor=100.0
    )
    print(f"Animal NOAEL: {safety['animal_noael_mg_kg']} mg/kg")
    print(f"HED: {safety['hed_mg_kg']:.2f} mg/kg")
    print(f"Safe concentration: {safety['safe_concentration_percent']:.4f}%")
    print(f"Assessment: {safety['assessment']}")
