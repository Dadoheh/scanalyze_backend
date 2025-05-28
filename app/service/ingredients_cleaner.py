import re
from typing import List

# WHY 'benzyl salicylate', 'parfum. ww'] WW AT THE END?

class IngredientsCleaner:
    # Lista typowych słów wprowadzających listę składników
    INGREDIENTS_MARKERS = [
        "ingredients:", "ingredients", "składniki:", "składniki", "inci:", "inci",
        "zawiera:", "zawiera", "skład:", "skład", "contains:", "contains"
    ]
    
    def __init__(self):
        """
        Initializes the product analyzer.
        """
        pass
        
    def extract_ingredients_from_text(self, text: str) -> List[str]:
        """
        Extracts a list of ingredients from OCR text.
        
        Args:
            text: OCR text to analyze
            
        Returns:
            A list of cleaned ingredients
        """
        text = " ".join(text.lower().split())
        
        ingredients_section = ""
        for marker in self.INGREDIENTS_MARKERS:
            if marker in text:
                parts = text.split(marker, 1)
                if len(parts) > 1:
                    ingredients_section = parts[1].strip()
                    break
        
        if not ingredients_section:
            return []
        
        end_patterns = ["\n\n", "\r\n\r\n", "\. ", " made in", " wyprodukowano w", " best before"]
        for pattern in end_patterns:
            if pattern in ingredients_section:
                ingredients_section = ingredients_section.split(pattern, 1)[0]
        
        ingredients_section = re.sub(r'[•\*\+\-]', '', ingredients_section)
        raw_ingredients = [i.strip() for i in ingredients_section.split(',')]
        
        clean_ingredients = []
        for ingredient in raw_ingredients:
            ingredient = re.sub(r'\([^)]*\)', '', ingredient)
            #ingredient = re.sub(r'\d+%?', '', ingredient)
            ingredient = ingredient.strip()
            
            if len(ingredient) < 3:
                continue
                
            
            # WHY 'benzyl salicylate', 'parfum. ww'] WW AT THE END?
            
            if ingredient and not any(stop_word in ingredient for stop_word in ["www.", ".com", "uwagi", "note:", "przyp"]):
                clean_ingredients.append(ingredient)
        
        return clean_ingredients

    def clean_text(self, text: str) -> str:
        """
        
        Args:
            
        Returns:
        """
        text = " ".join(text.split())
        text = text.lower()
        text = re.sub(r'[^\w\s,.:;()\-]', '', text)
        
        return text
    
    
    # def analyze_ingredients(self, ingredients: List[str], user_profile: Dict[str, Any]) -> Dict[str, Any]:
    #     """
        
    #     Args:
            
    #     Returns:
    #     """
    #     analyzed_ingredients = []
    #     compatibility_score = 0
    #     recommendation = "Brak rekomendacji"
       
    #     return {
    #         "ingredients": analyzed_ingredients,
    #         "compatibility_score": compatibility_score,
    #         "recommendation": recommendation
    #     }
        
