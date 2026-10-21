import os
from dotenv import load_dotenv
import requests
import pandas as pd
import duckdb

load_dotenv()
KEY = os.getenv("US_CENSUS_KEY")

DB_PATH = "market.duckdb"
CBP_TERRITORY_CODES = {
    "60", # American Samoa
    "66", # Guam
    "69", # Northern Mariana Islands
    "72", # Puerto Rico
    "78", # US Virgin Islands
}
CBP_COLUMN_NAMES = {
    "EMP": "employment",
    "ESTAB": "establishments",
    "PAYANN": "annual_payroll_thousands",
    "state": "state_code",
    "NAICS2017": "naics_code",
    "INDLEVEL": "industry_level",
}

def fetch_cbp_data(year, naics_code):
    """ Fetches County Business Patterns (CBP) data for a given year and NAICS code from the US Census API. """
    params = {
        "get": "EMP,ESTAB,PAYANN,INDLEVEL",
        "for": "state:*",
        "NAICS2017": naics_code,
        "key": KEY,
    }
    response = requests.get(f"https://api.census.gov/data/{year}/cbp", params=params)
    if response.status_code != 200:
        raise ValueError(
            f"CBP request failed for year={year}, naics={naics_code}: "
            f"status {response.status_code} {response.text}"
        )
    data = response.json()
    df = pd.DataFrame(data[1:], columns=data[0])
    return df

def clean_cbp_data(df, year):
    """Converts numbers, removes territories, renames columns, adds the year and checks for duplicates."""

    df = df.copy()
    df['EMP'] = pd.to_numeric(df['EMP'], errors='coerce')
    df['ESTAB'] = pd.to_numeric(df['ESTAB'], errors='coerce')
    df['PAYANN'] = pd.to_numeric(df['PAYANN'], errors='coerce')
    df['INDLEVEL'] = pd.to_numeric(df['INDLEVEL'], errors='coerce')

    df = df[~df['state'].isin(CBP_TERRITORY_CODES)]

    df = df.rename(columns=CBP_COLUMN_NAMES)
    df["year"] = year
    df = df.sort_values(["naics_code", "state_code", "year"])
    df = df.reset_index(drop=True)
    duplicate_rows = df.duplicated(subset=["naics_code", "state_code", "year"])
    if duplicate_rows.any():
        raise ValueError(f"{duplicate_rows.sum()} duplicate rows found in the cleaned DataFrame.")
    return df

def save_data(df, table_name):
    """ Saves the DataFrame to a DuckDB table. """
    with duckdb.connect(DB_PATH) as con:
        con.sql(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df")

def main():
    year = 2022
    raw = fetch_cbp_data(year, "*")
    df = clean_cbp_data(raw, year)
    save_data(df, "cbp")
    print(f"Saved {len(df)} rows ({df['naics_code'].nunique()} NAICS codes) to cbp")

if __name__ == "__main__":
    main()
