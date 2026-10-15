"""Download the UCI Online Retail II dataset and save it as one Parquet file.

Run from the project root:  python scripts/download_data.py
"""
import io
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
OUT = Path(__file__).resolve().parents[1] / "data" / "online_retail_ii.parquet"


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    print("Downloading (~45 MB)...")
    raw = urllib.request.urlopen(URL).read()
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        xlsx = z.read([n for n in z.namelist() if n.endswith(".xlsx")][0])
    print("Reading both Excel sheets (takes a few minutes)...")
    sheets = pd.read_excel(io.BytesIO(xlsx), sheet_name=None, dtype={"Invoice": str, "StockCode": str, "Description": str})
    df = pd.concat(sheets.values(), ignore_index=True)
    df.columns = [c.replace(" ", "_") for c in df.columns]
    df.to_parquet(OUT, index=False)
    print(f"Saved {len(df):,} rows to {OUT}")


if __name__ == "__main__":
    main()
