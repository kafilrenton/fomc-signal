import os
from pathlib import Path
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

URL = "https://www.frbsf.org/wp-content/uploads/USMPD.xlsx"
DATASETS = Path(__file__).resolve().parents[2] / "datasets"


# Fetcher function

def ensure_usmpd() -> Path:
    """Return the local USMPD.xlsx path, downloading it if missing."""

    path = DATASETS / "USMPD.xlsx"
    if not path.exists():
        DATASETS.mkdir(exist_ok=True)
        r = requests.get(URL)
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


# CSV builder functions

def build_statement_yields() -> pd.DataFrame:
    """Join statement-window yield changes to statement dates."""

    stmts = pd.read_csv(DATASETS / "statement.csv", parse_dates=["date"])
    stmts["date"] = stmts["date"].dt.date

    merged = stmts[["date"]].merge(load_sheet("Statements"), on="date", how="left")

    print(f"statement_yields.csv: {merged['ust2y_bp'].notna().sum()}/{len(merged)} matched")
    merged.to_csv(DATASETS / "statement_yields.csv", index=False)
    return merged


def build_minutes_yields() -> pd.DataFrame:
    """Join minutes-window yield changes to minutes release dates."""

    mins = pd.read_csv(DATASETS / "minutes.csv", parse_dates=["minutes_release"])
    mins["release_date"] = mins["minutes_release"].dt.date

    # Rename USMPD's Date to release_date so the join key is the same
    targets = load_sheet("Minutes").rename(columns={"date": "release_date"})

    merged = mins[["date", "release_date"]].merge(targets, on="release_date", how="left")

    print(f"minutes_yields.csv: {merged['ust2y_bp'].notna().sum()}/{len(merged)} matched")
    merged.to_csv(DATASETS / "minutes_yields.csv", index=False)
    return merged


def build_conference_yields() -> pd.DataFrame:
    """Join press-conference-window yield changes to meeting dates."""

    conf = pd.read_csv(DATASETS / "conference.csv", parse_dates=["date"])
    conf["date"] = conf["date"].dt.date

    merged = conf[["date"]].merge(load_sheet("Press Conferences"), on="date", how="left")

    print(f"conference_yields.csv: {merged['ust2y_bp'].notna().sum()}/{len(merged)} matched")
    merged.to_csv(DATASETS / "conference_yields.csv", index=False)
    return merged


def build_daily_fred_data() -> pd.DataFrame:
    """Download daily Fed Funds rate and Treasury yields from FRED API."""

    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise ValueError("FRED_API_KEY not found in .env")

    series_ids = {"DFF": "fed_funds", "DGS2": "ust2y", "DGS10": "ust10y"}
    dfs = []

    for series_id, col_name in series_ids.items():

        # FRED API JSON endpoint
        url = (
            f"https://api.stlouisfed.org/fred/series/observations?"
            f"series_id={series_id}&api_key={api_key}"
            f"&file_type=json&observation_start=2000-01-01"
        )
        
        r = requests.get(url)
        r.raise_for_status()
        
        # Parse JSON and set date column as index for alignment
        df = pd.DataFrame(r.json()["observations"])[["date", "value"]]
        df = df.set_index("date")
        
        # Handling any non-numeric data to return NaN 
        df[col_name] = pd.to_numeric(df["value"], errors="coerce")
        dfs.append(df[col_name])

    # Concat the series by date and drop rows with missing values
    merged = pd.concat(dfs, axis=1).dropna().reset_index()

    merged.to_csv(DATASETS / "daily_yields.csv", index=False)
    print(f"daily_yields.csv saved: {len(merged)} rows")
    return merged


if __name__ == "__main__":
    build_statement_yields()
    build_minutes_yields()
    build_conference_yields()
    build_daily_fred_data()