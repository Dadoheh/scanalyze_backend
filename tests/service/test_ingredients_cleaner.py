import pytest
from app.service.ingredients_cleaner import IngredientsCleaner

class TestIngredientsCleaner:

    @pytest.fixture
    def cleaner(self):
        return IngredientsCleaner()

    def test_extract_ingredients_empty_text(self, cleaner):
        result = cleaner.extract_ingredients_from_text("")
        assert result == []

    def test_extract_ingredients_no_markers(self, cleaner):
        text = "This is some text without ingredient markers"
        result = cleaner.extract_ingredients_from_text(text)
        assert result == []

    def test_extract_ingredients_real_example(self, cleaner):
        text = """NIVEA® Soft
         to wysoce skuteczny krem                                                
         nawilzajacy do codziennej pielegnacji.
         Stosuj wmasowując krem w oczyszczoną
         skórę twarzy. Omijaj okolice oczu.

         Nr art. 89095 Beiersdorf
         lersdorf AG, D-20245 Hamburg

         50mlI© ee
         www.NIVEA.pl PL Infolinia: 801 888 888
         Ingredients: Aqua, Glycerin, Paraffinum Liquidum, Myristyl Alcohol, Butylene Glycol,
         Alcohol Denat., Stearic Acid, Myristyl Myristate, Cera Microcristallina, Glyceryl Stearate,
         Hydrogenated Coco-Glycerides, Simmondsia Chinensis Seed Oil, Tocophery! Acetate,
         Lanolin Alcohol (Eucerit©), Polyglyceryl-2 Caprate, Dimethicone, Sodium Carbomer,
         Phenoxyethanol, Linalool, Citronellol, Alpha-Isomethyl lonone, Butylpheny! Methylpropional,

         Limonene, Benzyl Alcohol, Benzyl Salicylate, Parfum."""
         
        result = cleaner.extract_ingredients_from_text(text)
        
        print(f"Extracted ingredients: {result}")
        
        assert len(result) > 10
        assert "aqua" in result
        assert "glycerin" in result
        assert "paraffinum liquidum" in result
        assert "benzyl salicylate" in result
        
        assert not any("nivea" in ing for ing in result)
        assert not any("www" in ing for ing in result)
        assert not any("infolinia" in ing for ing in result)

    def test_extract_ingredients_different_markers(self, cleaner):
        markers_texts = {
            "ingredients:": "Some text ingredients: aqua, glycerin, parfum",
            "składniki:": "Some text składniki: woda, gliceryna, perfum",
            "inci:": "Some text inci: aqua, glycerin, parfum",
            "skład:": "Some text skład: woda, gliceryna, perfum"
        }
        
        for marker, text in markers_texts.items():
            result = cleaner.extract_ingredients_from_text(text)
            assert len(result) == 3, f"Failed with marker: {marker}"

    def test_extract_ingredients_with_parentheses(self, cleaner):
        text = "ingredients: aqua, glycerin (plant derived), parfum (fragrance)"
        result = cleaner.extract_ingredients_from_text(text)
        assert len(result) == 3
        assert "glycerin" in result  # parentheses content should be removed
        assert "plant derived" not in " ".join(result)

    def test_extract_ingredients_short_ingredients_filtered(self, cleaner):
        text = "ingredients: aqua, a, ab, glycerin"
        result = cleaner.extract_ingredients_from_text(text)
        assert len(result) == 2
        assert "aqua" in result
        assert "glycerin" in result
        assert "a" not in result  # too short, < 3 chars
        assert "ab" not in result  # too short, < 3 chars

    def test_extract_ingredients_with_stop_words(self, cleaner):
        text = "ingredients: aqua, glycerin, www.example.com, note: use daily"
        result = cleaner.extract_ingredients_from_text(text)
        assert "aqua" in result
        assert "glycerin" in result
        assert not any("www" in ing for ing in result)
        assert not any("note:" in ing for ing in result)

    def test_clean_text(self, cleaner):
        text = "This   is some TEXT! with (special) chars: 123;"
        result = cleaner.clean_text(text)
        assert result == "this is some text with (special) chars: 123;"

    def test_clean_text_special_characters(self, cleaner):
        text = "Test@#$%^&*()_+-=[]{}|;':\",./<>?`~"
        result = cleaner.clean_text(text)
        
        assert "(" in result and ")" in result
        assert "," in result and "." in result
        assert ":" in result and ";" in result
        assert "-" in result
        
        assert "@" not in result
        assert "#" not in result
        assert "$" not in result