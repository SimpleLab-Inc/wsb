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

# Remove empty geometries
ucmr = ucmr[(~ucmr["geometry"].is_empty) & ucmr["geometry"].notna()]

# Aggregate polygons so pwsid is unique
ucmr = (ucmr[["pwsid", "geometry"]]
    .dissolve(by="pwsid")
    .reset_index())


#%%

df = gpd.GeoDataFrame().assign(
    source_system_id    = ucmr["pwsid"],
    source_system       = "ucmr",
    xref_id             = "ucmr." + ucmr["pwsid"],
    master_key          = ucmr["pwsid"],
    geometry            = ucmr["geometry"],
    geometry_quality    = "Zip code boundary"
)

#%%

helpers.load_to_postgis("ucmr", df)