import pytest
from unittest.mock import AsyncMock, patch
from app.service.chemical_identity_mapper import ChemicalIdentityMapper
from app.models.chemical_identity import ChemicalIdentityResult

class TestChemicalIdentityMapper:
    
    @pytest.fixture
    def mapper(self):
        return ChemicalIdentityMapper()
    
    @pytest.fixture
    def mock_pubchem_responses_aqua(self):
        """Mock HTTP responses for aqua from PubChem API."""
        return [
            AsyncMock(json=lambda: {"IdentifierList": {"CID": [962]}}),
            AsyncMock(json=lambda: {
                "PropertyTable": {
                    "Properties": [{
                        "CanonicalSMILES": "O",
                        "InChI": "InChI=1S/H2O/h1H2",
                        "InChIKey": "XLYOFNOQVPJJNP-UHFFFAOYSA-N",
                        "MolecularFormula": "H2O",
                        "MolecularWeight": "18.015"
                    }]
                }
            }),
            AsyncMock(json=lambda: {
                "InformationList": {
                    "Information": [{
                        "Synonym": ["water", "aqua", "7732-18-5", "H2O"]
                    }]
                }
            })
        ]
    
    @pytest.fixture
    def mock_pubchem_responses_glycerin(self):
        """Mock HTTP responses for glycerin from PubChem API."""
        return [
            AsyncMock(json=lambda: {"IdentifierList": {"CID": [753]}}),
            AsyncMock(json=lambda: {
                "PropertyTable": {
                    "Properties": [{
                        "CanonicalSMILES": "C(C(CO)O)O",
                        "InChI": "InChI=1S/C3H8O3/c4-1-3(6)2-5/h3-6H,1-2H2",
                        "InChIKey": "PEDCQBHIVMGVHV-UHFFFAOYSA-N",
                        "MolecularFormula": "C3H8O3",
                        "MolecularWeight": "92.09"
                    }]
                }
            }),
            AsyncMock(json=lambda: {
                "InformationList": {
                    "Information": [{
                        "Synonym": ["glycerol", "glycerin", "56-81-5", "1,2,3-propanetriol"]
                    }]
                }
            })
        ]
    
    @pytest.fixture
    def mock_pubchem_responses_generic(self):
        """Generic mock responses for batch testing."""
        return [
            AsyncMock(json=lambda: {"IdentifierList": {"CID": [123]}}),
            AsyncMock(json=lambda: {
                "PropertyTable": {"Properties": [{"CanonicalSMILES": "CCO"}]}
            }),
            AsyncMock(json=lambda: {
                "InformationList": {"Information": [{"Synonym": ["test", "123-45-6"]}]}
            })
        ]
    
    @pytest.fixture
    def mock_pubchem_not_found(self):
        """Mock response when ingredient not found."""
        return AsyncMock(json=lambda: {"Fault": {"Code": "PUGREST.NotFound"}})

    @pytest.mark.asyncio
    async def test_map_ingredient_success_pubchem(self, mapper, mock_pubchem_responses_aqua):
        """Test successful mapping using PubChem scraper."""
        
        all_responses = mock_pubchem_responses_aqua * 2
        
        with patch('app.scrapers.base_scraper.BaseScraper._make_request') as mock_request:
            mock_request.side_effect = all_responses
            
            result = await mapper.map_ingredient("aqua")
            
            assert result.found is True
            assert result.inci_name == "aqua"
            assert result.identifiers is not None
            assert result.identifiers.cas_number == "7732-18-5"
            assert result.identifiers.smiles == "O"
            assert result.identifiers.source == "pubchem"
            assert "pubchem" in result.sources_checked
            assert result.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_map_ingredient_success_glycerin(self, mapper, mock_pubchem_responses_glycerin):
        """Test successful mapping of glycerin."""
        
        all_responses = mock_pubchem_responses_glycerin * 2
        
        with patch('app.scrapers.base_scraper.BaseScraper._make_request') as mock_request:
            mock_request.side_effect = all_responses
            
            result = await mapper.map_ingredient("glycerin")
            
            assert result.found is True
            assert result.identifiers.cas_number == "56-81-5"
            assert result.identifiers.smiles == "C(C(CO)O)O"
            assert result.identifiers.molecular_formula == "C3H8O3"

    @pytest.mark.asyncio
    async def test_map_ingredient_pubchem_not_found(self, mapper, mock_pubchem_not_found):
        """Test when PubChem doesn't find ingredient."""
        
        with patch('app.scrapers.base_scraper.BaseScraper._make_request') as mock_request:
            mock_request.return_value = mock_pubchem_not_found
            
            result = await mapper.map_ingredient("unknown-ingredient")
            
            assert result.found is False
            assert result.identifiers is None
            assert len(result.comprehensive_data.sources_used) == 0
            assert result.comprehensive_data is not None

    @pytest.mark.asyncio
    async def test_map_ingredient_with_pubchem_exception(self, mapper):
        """Test handling of HTTP exceptions."""
        
        with patch('app.scrapers.base_scraper.BaseScraper._make_request') as mock_request:
            mock_request.side_effect = Exception("Network timeout")
            
            result = await mapper.map_ingredient("test")
            
            assert result.found is False
            assert result.identifiers is None

            condition_met = (
                len(result.errors) > 0 or
                (result.comprehensive_data and 
                result.comprehensive_data.basic_identifiers is None and
                result.comprehensive_data.toxicology is None and
                result.comprehensive_data.regulatory is None and
                result.comprehensive_data.physical_chemical is None)
            )
            assert condition_met, "Expected errors or all domains to be None"
            assert result.comprehensive_data is not None

    @pytest.mark.asyncio
    async def test_map_ingredients_batch_pubchem(self, mapper, mock_pubchem_responses_generic):
        """Test batch processing of multiple ingredients."""
        ingredients = ["aqua", "glycerin", "parfum"]
        
        all_responses = mock_pubchem_responses_generic * len(ingredients) * 2
        
        with patch('app.scrapers.base_scraper.BaseScraper._make_request') as mock_request:
            mock_request.side_effect = all_responses
            
            results = await mapper.map_ingredients_batch(ingredients)
            
            assert len(results) == 3
            assert all(isinstance(r, ChemicalIdentityResult) for r in results)
            assert all(r.found for r in results)

    @pytest.mark.asyncio
    async def test_map_ingredients_batch_with_batching(self, mapper, mock_pubchem_responses_generic):
        """Test batch processing with sleep between batches."""
        ingredients = [f"ingredient_{i}" for i in range(7)]
        
        all_responses = mock_pubchem_responses_generic * len(ingredients) * 2
        
        with patch('app.scrapers.base_scraper.BaseScraper._make_request') as mock_request, \
             patch('asyncio.sleep') as mock_sleep:
            
            mock_request.side_effect = all_responses
            
            results = await mapper.map_ingredients_batch(ingredients)
            
            assert len(results) == 7
            for call in mock_sleep.call_args_list:
                assert call[0][0] == 0.1

    @pytest.mark.asyncio
    async def test_map_ingredient_pubchem_partial_data(self, mapper):
        """Test mapping with partial PubChem data."""
        
        partial_responses = [
            AsyncMock(json=lambda: {"IdentifierList": {"CID": [123]}}),
            AsyncMock(json=lambda: {
                "PropertyTable": {
                    "Properties": [{
                        "CanonicalSMILES": "CCO"
                    }]
                }
            }),
            AsyncMock(json=lambda: {
                "InformationList": {
                    "Information": [{
                        "Synonym": ["ethanol", "123-45-6"]
                    }]
                }
            })
        ]
        
        all_responses = partial_responses * 2
        
        with patch('app.scrapers.base_scraper.BaseScraper._make_request') as mock_request:
            mock_request.side_effect = all_responses
            
            result = await mapper.map_ingredient("test-ingredient")
            
            assert result.found is True
            assert result.identifiers.cas_number == "123-45-6"
            assert result.identifiers.smiles == "CCO"
            