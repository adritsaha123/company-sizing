import os
from dotenv import load_dotenv
import requests
import pandas as pd
import duckdb

load_dotenv()
KEY = os.getenv("US_CENSUS_KEY")
CBP_YEAR = 2022
CBP_URL = f"https://api.census.gov/data/{CBP_YEAR}/cbp"
CBP_TERRITORY_CODES = {
    "60", # American Samoa
    "66", # Guam
    "69", # Northern Mariana Islands
    "72", # Puerto Rico
    "78", # US Virgin Islands
}
DB_PATH = "market.duckdb"


def main():
    params = {
        "get": "EMP,ESTAB,PAYANN",
        "for": "state:*",
        "NAICS2017": "72",
        "key": KEY,
    }

    rename = {
        "EMP": "employment",
        "ESTAB": "establishments",
        "PAYANN": "annual_payroll_thousands",
        "state": "state_code",
        "NAICS2017": "naics_code",
    }


    response = requests.get(CBP_URL, params=params)
    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data[1:], columns=data[0])

        df['EMP'] = pd.to_numeric(df['EMP'], errors='coerce')
        df['ESTAB'] = pd.to_numeric(df['ESTAB'], errors='coerce')
        df['PAYANN'] = pd.to_numeric(df['PAYANN'], errors='coerce')

        df = df[~df['state'].isin(CBP_TERRITORY_CODES)]


        df = df.rename(columns=rename)
        df["year"] = CBP_YEAR
        df = df.sort_values("state_code")
        df = df.reset_index(drop=True)

        con = duckdb.connect(DB_PATH)
        con.sql("CREATE OR REPLACE TABLE cbp AS SELECT * FROM df")
        con.sql("SELECT * FROM cbp LIMIT 5").show()
        con.sql("SELECT COUNT(*) FROM cbp").show()
        con.close()
    else:
        print(f"Error: {response.status_code} - {response.text}")
if __name__ == "__main__":
    main()
