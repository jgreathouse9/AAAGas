import os
import sys
from pathlib import Path

from hypothesis import settings

# The county scraper is run as a script from RealCounty/, which imports countyutils as a top-level module
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "RealCounty"))

# "ci" is deterministic: CI and mutation runs must not pass or fail on an unlucky draw
settings.register_profile("dev", deadline=None)
settings.register_profile("ci", deadline=None, derandomize=True)
settings.load_profile(os.environ.get("AAAGAS_HYPOTHESIS_PROFILE", "dev"))
