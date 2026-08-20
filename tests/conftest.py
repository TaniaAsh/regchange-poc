import sys
from pathlib import Path

# Mirrors how Azure Functions runs this app: working directory is
# src/function_app/, and `pipeline` is a plain subpackage of it.
FUNCTION_APP_ROOT = Path(__file__).resolve().parent.parent / "src" / "function_app"
sys.path.insert(0, str(FUNCTION_APP_ROOT))
