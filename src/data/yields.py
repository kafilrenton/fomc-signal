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


# Function providing main data of interest from USMPD

def load_sheet(sheet: str) -> pd.DataFrame:
    """Return the given USMPD sheet with standard date and base points columns."""

    df = pd.read_excel(ensure_usmpd(), sheet_name=sheet)

    # USMPD timestamps include time of day, stripping to plain date for joining
    df["date"] = pd.to_datetime(df["Date"]).dt.date

    df["ust2y_bp"] = df["UST2Y"] * 100
    df["ust10y_bp"] = df["UST10Y"] * 100
    df["2s10s_bp"] = df["ust10y_bp"] - df["ust2y_bp"]

    # Market-implied rate surprises, for testing stance beyond what was priced in
    df["mp1_bp"] = df["MP1"] * 100
    df["mp2_bp"] = df["MP2"] * 100

    return df[["date", "ust2y_bp", "ust10y_bp", "2s10s_bp", "mp1_bp", "mp2_bp"]]