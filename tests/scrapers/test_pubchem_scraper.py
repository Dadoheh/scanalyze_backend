import pytest
from unittest.mock import AsyncMock, patch
import httpx
from app.scrapers.pubchem_scraper import PubChemScraper

class TestPubChemScraper:
    
    @pytest.fixture
    def scraper(self):
        return PubChemScraper()
    
    @pytest.fixture
    def mock_cid_response(self):
        return {
            "IdentifierList": {
                "CID": [753]
            }
        }
    
    @pytest.fixture
    def mock_properties_response(self):
        return {
            "PropertyTable": {
                "Properties": [{
                    "CID": 753,
                    "MolecularFormula": "C3H8O3",
                    "MolecularWeight": "92.09",
                    "CanonicalSMILES": "C(C(CO)O)O",
                    "InChI": "InChI=1S/C3H8O3/c4-1-3(6)2-5/h3-6H,1-2H2",
                    "InChIKey": "PEDCQBHIVMGVHV-UHFFFAOYSA-N"
                }]
            }
        }
    
    @pytest.fixture
    def mock_synonyms_response(self):
        return {
            "InformationList": {
                "Information": [{
                    "CID": 753,
                    "Synonym": [
                        "glycerol",
                        "glycerin",
                        "56-81-5",  # CAS number
                        "1,2,3-propanetriol",
                        "MFCD00004722"
                    ]
                }]
            }
        }

    @pytest.mark.asyncio
    async def test_search_by_name_success(self, scraper, mock_cid_response, 
                                        mock_properties_response, mock_synonyms_response):
        """Test successful search by ingredient name."""
        with patch.object(scraper, '_make_request') as mock_request:
            mock_responses = [
                AsyncMock(json=lambda: mock_cid_response),  # CID call
                AsyncMock(json=lambda: {"PropertyTable": {"Properties": [{"MolecularFormula": "C3H8O3"}]}}),
                AsyncMock(json=lambda: {"PropertyTable": {"Properties": [{"MolecularWeight": "92.09"}]}}),
                AsyncMock(json=lambda: {"PropertyTable": {"Properties": [{"CanonicalSMILES": "C(C(CO)O)O"}]}}),
                AsyncMock(json=lambda: {"PropertyTable": {"Properties": [{"InChI": "InChI=1S/C3H8O3/c4-1-3(6)2-5/h3-6H,1-2H2"}]}}),
                AsyncMock(json=lambda: {"PropertyTable": {"Properties": [{"InChIKey": "PEDCQBHIVMGVHV-UHFFFAOYSA-N"}]}}),
                AsyncMock(json=lambda: mock_synonyms_response)  # Synonyms call
            ]
            mock_request.side_effect = mock_responses
            
            result = await scraper.search_by_name("glycerin")
            
            assert result["found"] is True
            assert result["source"] == "pubchem"
            assert result["inci_name"] == "glycerin"
            assert result["cas_number"] == "56-81-5"
            assert result["smiles"] == "C(C(CO)O)O"
            assert result["inchi"] == "InChI=1S/C3H8O3/c4-1-3(6)2-5/h3-6H,1-2H2"
            assert result["molecular_formula"] == "C3H8O3"
            assert result["confidence_score"] == 0.8

    @pytest.mark.asyncio
    async def test_search_by_name_no_cid_found(self, scraper):
        """Test when PubChem doesn't find CID for ingredient."""
        mock_response = {"Fault": {"Code": "PUGREST.NotFound"}}
        
        with patch.object(scraper, '_make_request') as mock_request:
            mock_request.return_value = AsyncMock(json=lambda: mock_response)
            
            result = await scraper.search_by_name("unknown-ingredient")
            
            assert result["found"] is False
            assert result["source"] == "pubchem"
            assert result["inci_name"] == "unknown-ingredient"

    @pytest.mark.asyncio
    async def test_search_by_name_empty_cid_list(self, scraper):
        """Test when PubChem returns empty CID list."""
        mock_response = {"IdentifierList": {"CID": []}}
        
        with patch.object(scraper, '_make_request') as mock_request:
            mock_request.return_value = AsyncMock(json=lambda: mock_response)
            
            result = await scraper.search_by_name("unknown-ingredient")
            
            assert result["found"] is False

    @pytest.mark.asyncio
    async def test_search_with_network_error(self, scraper):
        """Test handling of network errors."""
        with patch.object(scraper, '_make_request') as mock_request:
            mock_request.side_effect = Exception("Network timeout")
            
            result = await scraper.search_by_name("glycerin")
            
            assert result["found"] is False
            assert "error" in result
            assert "Network timeout" in result["error"]

    @pytest.mark.asyncio
    async def test_parse_pubchem_data_with_cas(self, scraper):
        """Test parsing of PubChem data with CAS number in synonyms."""
        properties = {
            "PropertyTable": {
                "Properties": [{
                    "smiles": "CCO",
                    "inchi": "InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3"
                }]
            }
        }
        synonyms = {
            "InformationList": {
                "Information": [{
                    "Synonym": ["ethanol", "64-17-5", "ethyl alcohol"]
                }]
            }
        }
        
        result = scraper._parse_pubchem_data(properties, synonyms, "ethanol")
        
        assert result["cas_number"] == "64-17-5"
        assert result["smiles"] == "CCO"
        assert result["found"] is True

    @pytest.mark.asyncio
    async def test_parse_pubchem_data_no_cas(self, scraper):
        """Test parsing when no CAS number is found in synonyms."""
        properties = {
            "PropertyTable": {
                "Properties": [{
                    "smiles": "CCO"
                }]
            }
        }
        synonyms = {
            "InformationList": {
                "Information": [{
                    "Synonym": ["ethanol", "ethyl alcohol", "grain alcohol"]
                }]
            }
        }
        
        result = scraper._parse_pubchem_data(properties, synonyms, "ethanol")
        
        assert "cas_number" not in result or result["cas_number"] is None
        assert result["smiles"] == "CCO"
        assert result["found"] is True

    @pytest.mark.asyncio
    async def test_search_by_cas_delegates_to_search_by_name(self, scraper):
        """Test that search_by_cas properly delegates to search_by_name."""
        with patch.object(scraper, 'search_by_name') as mock_search_by_name:
            mock_search_by_name.return_value = {"found": True, "test": "data"}
            
            result = await scraper.search_by_cas("64-17-5")
            
            mock_search_by_name.assert_called_once_with("64-17-5")
            assert result == {"found": True, "test": "data"}

    @pytest.mark.asyncio
    async def test_rate_limiting(self, scraper):
        """Test that rate limiting is working."""
        import time
        
        with patch.object(scraper, '_make_request') as mock_request:
            mock_request.return_value = AsyncMock(json=lambda: {"IdentifierList": {"CID": []}})
            
            start_time = time.time()
            await scraper.search_by_name("test1")
            await scraper.search_by_name("test2")
            end_time = time.time()
