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
state_cw = (pd
    .read_csv("../crosswalks/state_fips_to_abbr.csv", dtype="str")
    .set_index("code"))

#%%

tiger = gpd.read_file(os.path.join(DATA_PATH, "tigris_places_clean.geojson"))

# Ensure strings with leading zeros
tiger["statefp"] = tiger["statefp"].astype("int").astype("str").str.zfill(2)

# Augment with state code
tiger = (tiger
    .join(state_cw, on="statefp", how="left"))

# TODO - It would be nice to also know county, zip code, etc.,
# but it doesn't seem like we can get this from the data as it stands.
# Might need a lookup table. 

#%%

df = gpd.GeoDataFrame().assign(
    source_system_id    = tiger["geoid"],
    source_system       = "tiger",
    contributor_id      = "tiger." + tiger["geoid"],
    master_key          = "UNK-tiger." + tiger["geoid"],
    name                = tiger["name"],
    state               = tiger["state"],
    population_served_count = tiger["population"].astype(pd.Int64Dtype()),
    geometry            = tiger["geometry"],
    geometry_quality    = "Tiger boundary"
)

#%%

helpers.load_to_postgis("tiger", df)