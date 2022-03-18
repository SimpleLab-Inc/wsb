import os
from typing import Optional

import sqlalchemy as sa
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

DATA_PATH = os.environ["WSB_STAGING_PATH"]


def load_to_postgis(source_system: str, df: pd.DataFrame):

    conn = sa.create_engine(os.environ["POSTGIS_CONN_STR"])
    TARGET_TABLE = "utility_xref"

    print(f"Removing existing {source_system} data from database...", end="")
    conn.execute(f"DELETE FROM {TARGET_TABLE} WHERE source_system = '{source_system}';")
    print("done")

    print(f"Loading {source_system} to database...", end="")
    df.to_postgis(TARGET_TABLE, conn, if_exists="append")
    print("done.")

    print("Applying SQL cleanse...")
    _sql_cleanse(source_system)
    print("done.")


def get_pwsids_of_interest():

    sdwis = pd.read_csv(
        DATA_PATH + "/sdwis_water_system.csv",
        usecols=["pwsid", "pws_activity_code", "pws_type_code"],
        dtype="string")

    # Filter to only active community water systems
    # Starts as 400k, drops to ~50k after this filter
    # Keep only "A" for active
    return sdwis.loc[
            (sdwis["pws_activity_code"].isin(["A"])) &
            (sdwis["pws_type_code"] == "CWS")
        ]["pwsid"]


# Pandas-based cleansing
# def _cleanse(df):
#     """
#     For now, we'll just apply this data cleaning script prior to the database save.
#     Later, we may want to save both the raw and the clean data to the database.
#     """

#     df = df.copy()

#     #####################
#     # Cleansing

#     # More cleansing on the unified model
#     df["zip"] = df["zip"].str[0:5]
#     df["name"] = df["name"].str.upper()
#     df["address_line_1"] = df["address_line_1"].str.upper()
#     df["address_line_2"] = df["address_line_2"].str.upper()
#     df["city"] = df["city"].str.upper()
#     df["state"] = df["state"].str.upper()
#     df["county"] = df["county"].str.upper()
#     df["city_served"] = df["city_served"].str.upper()

#     #####################
#     # Address Cleansing

#     # Null out zips "99999" - doesn't exist.
#     df.loc[df["zip"] == "99999", "zip"] = pd.NA

#     # Identify and remove administrative addresses
#     df["address_quality"] = pd.NA

#     # Any that have "PO BOX" are admin and should be removed
#     PO_BOX_REGEX = r"^P[\. ]?O\b\.? *BOX +\d+$"

#     mask = df["address_line_1"].fillna("").str.contains(PO_BOX_REGEX, regex=True)
#     df.loc[mask, "address_quality"] = "PO BOX" # May standardize later
#     df.loc[mask, "address_line_1"] = pd.NA

#     mask = df["address_line_2"].fillna("").str.contains(PO_BOX_REGEX, regex=True)
#     df.loc[mask, "address_quality"] = "PO BOX" # May standardize later
#     df.loc[mask, "address_line_2"] = pd.NA

#     # If there's an address in line 2 but not line 1, move it
#     mask = df["address_line_1"].isna() & df["address_line_2"].notna()
#     df.loc[mask, "address_line_1"] = df.loc[mask, "address_line_2"]
#     df.loc[mask, "address_line_2"] = pd.NA

#     return df


def _sql_cleanse(source_system: Optional[str]):

    conn = sa.create_engine(os.environ["POSTGIS_CONN_STR"])

    PO_BOX_REGEX = r'^P[\. ]?O\M\.? *BOX +\d+$'
 
    source_system_filter = "" if source_system is None else f"source_system = '{source_system}' AND"

    _run_cleanse_rule(conn,
        "NULL out nonexistent zip code '99999'",
        f"""
            UPDATE utility_xref
            SET zip = NULL
            WHERE
                {source_system_filter}
                zip = '99999';
        """)

    _run_cleanse_rule(conn,
        "Remove PO BOX from address_line_1",
        f"""
            UPDATE utility_xref
            SET
                address_quality = 'PO BOX',
                address_line_1 = NULL
            WHERE
                {source_system_filter}
                address_line_1 ~ '{PO_BOX_REGEX}';
        """)

    _run_cleanse_rule(conn,
        "Remove PO BOX from address_line_2",
        f"""
        UPDATE utility_xref
        SET
            address_quality = 'PO BOX',
            address_line_2 = NULL
        WHERE
            {source_system_filter}
            address_line_2 ~ '{PO_BOX_REGEX}';
        """)

    _run_cleanse_rule(conn,
        "If there's an address in line 2 but not line 1, move it",
        f"""
            UPDATE utility_xref
            SET
                address_line_1 = address_line_2,
                address_line_2 = NULL
            WHERE
                {source_system_filter}
                (address_line_1 IS NULL OR address_line_1 = '') AND
                address_line_2 IS NOT NULL;
        """)


def _run_cleanse_rule(conn, rule_name: str, sql: str):
    result = conn.execute(sql)
    print(f"Ran cleanse rule '{rule_name}': {result.rowcount} rows affected")