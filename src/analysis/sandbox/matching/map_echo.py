#%%

import os
import pandas as pd
import geopandas as gpd
import helpers
from dotenv import load_dotenv

load_dotenv()

DATA_PATH = os.environ["WSB_STAGING_PATH"]
EPSG = os.environ["WSB_EPSG"]

#%%

echo_df = pd.read_csv(
    DATA_PATH + "/echo.csv",
    usecols=[
        "pwsid", "fac_lat", "fac_long", "fac_name",
        "fac_street", "fac_city", "fac_state", "fac_zip", "fac_county", 
        'fac_collection_method', 'fac_reference_point', 'fac_accuracy_meters', 
        'fac_indian_cntry_flg', 'fac_percent_minority', 'fac_pop_den', 'ejscreen_flag_us'],
    dtype="string")

pwsids = helpers.get_pwsids_of_interest()

# Filter to only those in our SDWIS list and with lat/long
# 47,951 SDWIS match to ECHO, 1494 don't match
echo_df = echo_df.loc[
    echo_df["pwsid"].isin(pwsids) &
    echo_df["fac_lat"].notna()].copy()

# If fac_state is NA, copy from pwsid
mask = echo_df["fac_state"].isna()
echo_df.loc[mask, "fac_state"] = echo_df.loc[mask, "pwsid"].str[0:2]

# Convert to geopandas
echo: gpd.GeoDataFrame = gpd.GeoDataFrame(
    echo_df,
    geometry=gpd.points_from_xy(echo_df["fac_long"], echo_df["fac_lat"]),
    crs="EPSG:4326")

# Cleanse out "UNK"
echo = echo.replace({"UNK": pd.NA})

echo.head()

#%%

df = gpd.GeoDataFrame().assign(
    source_system_id        = echo["pwsid"],
    source_system           = "echo",
    contributor_id          = "echo." + echo["pwsid"],
    master_key              = echo["pwsid"],
    pwsid                   = echo["pwsid"],
    state                   = echo["fac_state"],
    name                    = echo["fac_name"],
    address_line_1          = echo["fac_street"],
    city                    = echo["fac_city"],
    county                  = echo["fac_county"],
    zip                     = echo["fac_zip"],
    geometry_lat            = echo["fac_lat"],
    geometry_long           = echo["fac_long"],
    geometry                = echo["geometry"],
    geometry_quality        = echo["fac_collection_method"],
)

#%%

helpers.load_to_postgis("echo", df)