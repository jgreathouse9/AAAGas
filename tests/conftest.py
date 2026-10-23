import sys
from pathlib import Path

# The county scraper is run as a script from RealCounty/, which imports countyutils as a top-level module
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "RealCounty"))
