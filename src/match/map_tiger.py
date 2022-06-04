#%%

import os
import pandas as pd
import geopandas as gpd
from dotenv import load_dotenv
import match.helpers as helpers

load_dotenv()

DATA_PATH = os.environ["WSB_STAGING_PATH"]
EPSG = os.environ["WSB_EPSG"]

# Bring in the FIPS -> State Abbr crosswalk
state_cw = pd.read_csv("../crosswalks/state_fips_to_abbr.csv").set_index("code")

county_cw = (
    pd.read_csv("../crosswalks/county_fips.csv", usecols=["code", "county"])
    .set_index("code"))

#%%

tiger = gpd.read_file(os.path.join(DATA_PATH, "tigris_places_clean.geojson"))

# keep_columns = ["STATEFP", "GEOID", "NAME", "NAMELSAD"]
# tiger = tiger[keep_columns]

# Standardize data type
tiger["statefp"] = tiger["statefp"].astype("int")
tiger["placefp"] = tiger["placefp"].astype("int")

# Augment with state code and county name
# Sometimes the "place" fips code is a state; sometimes it's a county.
tiger = (tiger
    .join(state_cw, on="statefp", how="left")
    .join(county_cw, on="placefp", how="left"))

# TODO - There's gotta be a way to get more complete county information. In the transformer?

# GEOID seems to be a safe unique identifier
tiger.head()

#%%

df = gpd.GeoDataFrame().assign(
    source_system_id    = tiger["geoid"],
    source_system       = "tiger",
    contributor_id      = "tiger." + tiger["geoid"],
    master_key          = "UNK-tiger." + tiger["geoid"],
    name                = tiger["name"],
    state               = tiger["state"],
    county              = tiger["county"],
    geometry            = tiger["geometry"],
    geometry_quality    = "Tiger boundary"
)

#%%

helpers.load_to_postgis("tiger", df)