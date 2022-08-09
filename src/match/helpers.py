import os
from typing import Optional

import sqlalchemy as sa
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

DATA_PATH = os.environ["WSB_STAGING_PATH"]


def load_to_postgis(source_system: str, df: pd.DataFrame):

    conn = sa.create_engine(os.environ["POSTGIS_CONN_STR"])
    TARGET_TABLE = "pws_contributors"

    print(f"Removing existing {source_system} data from database...", end="")
    conn.execute(f"DELETE FROM {TARGET_TABLE} WHERE source_system = '{source_system}';")
    print("done")

    print(f"Loading {source_system} to database...", end="")
    df.to_postgis(TARGET_TABLE, conn, if_exists="append")
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
