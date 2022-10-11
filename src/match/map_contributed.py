#%%

import os
import geopandas as gpd
import match.helpers as helpers
from dotenv import load_dotenv

load_dotenv()

DATA_PATH = os.environ["WSB_STAGING_PATH"]

#%%

contrib = gpd.read_file(os.path.join(DATA_PATH, "contributed_pws.geojson"))

#%%
# Check assumptions
assert contrib["pwsid"].is_unique

#%%

df = gpd.GeoDataFrame().assign(
    source_system_id        = contrib["pwsid"],
    source_system           = "contributed",
    contributor_id          = "contributed." + contrib["pwsid"],
    master_key              = contrib["pwsid"],
    pwsid                   = contrib["pwsid"],
    state                   = contrib["state"],
    name                    = contrib["pws_name"],
    geometry                = contrib["geometry"],
    centroid_lat            = contrib["centroid_lat"],
    centroid_lon            = contrib["centroid_long"],
    centroid_quality        = "CALCULATED FROM GEOMETRY",
)

#%%

helpers.load_to_postgis("contributed", df)