import sys, pathlib

# Ensure project src directory is on path for tests
PROJECT_ROOT = pathlib.Path(__file__).parent.parent
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
