#%%

import os
import pandas as pd
import geopandas as gpd
from dotenv import load_dotenv
import helpers

load_dotenv()

DATA_PATH = os.environ["WSB_STAGING_PATH"]
EPSG = os.environ["WSB_EPSG"]

#%%

tiger = gpd.read_file(DATA_PATH + "/tigris_places_clean.geojson")

# keep_columns = ["STATEFP", "GEOID", "NAME", "NAMELSAD"]
# tiger = tiger[keep_columns]

# Standardize data type
tiger["statefp"] = tiger["statefp"].astype("int")

# Augment with state abbrev
tiger = tiger.join(crosswalk, on="statefp", how="inner")

# GEOID seems to be a safe unique identifier
tiger.head()

#%%

df = gpd.GeoDataFrame().assign(
    source_system_id    = tiger["geoid"],
    source_system       = "tiger",
    xref_id             = "tiger." + tiger["geoid"],
    master_key          = "UNK-tiger." + tiger["geoid"],
    name                = tiger["name"],
    state               = tiger["state"],
    geometry            = tiger["geometry"],
    geometry_quality    = "Tiger boundary"
)

#%%

helpers.load_to_postgis("tiger", df)