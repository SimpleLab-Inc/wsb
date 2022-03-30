#%%

import os
import geopandas as gpd
from dotenv import load_dotenv
import helpers

load_dotenv()

DATA_PATH = os.environ["WSB_STAGING_PATH"]
EPSG = os.environ["WSB_EPSG"]

#%% 

# Primarily: This links pwsid to zip code.
# Primary Key: pwsid + zipcode (because pws's may serve more than one zip)

ucmr = gpd.read_file(DATA_PATH + "/ucmr.geojson")

#%%

# TODO: Could we get counties in this? Not currently present, but we could look it up from zip code.
# TODO: Could we get lat/long of centroid?

# Preserve the original data in memory (for troubleshooting)
agg = ucmr

# Remove empty geometries
#agg = agg[(~agg["geometry"].is_empty) & agg["geometry"].notna()]

# Aggregate polygons so pwsid is unique
# Dissolve function:
#  (1) Aggregates polygons with a unary_union and
#  (2) Aggregates other fields with a "first". This means we lose zip codes...but our model only allows for one anyway.
agg = (agg[["pwsid", "zipcode", "geometry"]]
    .dissolve(by="pwsid", aggfunc="first")
    .reset_index())

#%%

df = gpd.GeoDataFrame().assign(
    source_system_id    = agg["pwsid"],
    source_system       = "ucmr",
    contributor_id      = "ucmr." + agg["pwsid"],
    master_key          = agg["pwsid"],
    pwsid               = agg["pwsid"],
    zip                 = agg["zipcode"],
    geometry            = agg["geometry"],
    geometry_quality    = "Zip code boundary"
)

#%%

helpers.load_to_postgis("ucmr", df)