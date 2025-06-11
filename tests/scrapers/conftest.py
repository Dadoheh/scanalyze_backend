import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

@pytest.fixture
def sample_inci_ingredients():
    """Common INCI ingredients for testing."""
    return [
        "aqua",
        "glycerin", 
        "cetyl alcohol",
        "sodium lauryl sulfate",
        "parfum",
        "unknown-ingredient-xyz"
    ]

@pytest.fixture
def expected_chemical_data():
    """Expected chemical data for common ingredients."""
    return {
        "aqua": {
            "cas_number": "7732-18-5",
            "ec_number": "231-791-2",
            "smiles": "O"
        },
        "glycerin": {
            "cas_number": "56-81-5", 
            "smiles": "C(C(CO)O)O",
            "inchi": "InChI=1S/C3H8O3/c4-1-3(6)2-5/h3-6H,1-2H2"
        }
    }
    