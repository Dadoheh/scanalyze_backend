import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
os.environ["JWT_SECRET_KEY"] = "test_secret_key_for_testing"