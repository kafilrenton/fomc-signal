# Imports
from pathlib import Path
import pandas as pd
import requests

url = "https://www.frbsf.org/wp-content/uploads/USMPD.xlsx"
datasets = Path(__file__).resolve().parents[2] / "datasets"


# Fetcher function

def ensure_usmpd() -> Path:
    """Return the local USMPD.xlsx path, downloading it if missing."""

    path = datasets / "USMPD.xlsx"
    if not path.exists():
        datasets.mkdir(exist_ok=True)
        r = requests.get(url)
        r.raise_for_status()
        path.write_bytes(r.content)
    return path
