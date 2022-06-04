#%%

import os
import pandas as pd
import geopandas as gpd
from dotenv import load_dotenv
import match.helpers as helpers

load_dotenv()

DATA_PATH = os.environ["WSB_STAGING_PATH"]
EPSG = os.environ["WSB_EPSG"]

#%%
mhp = gpd.read_file(os.path.join(DATA_PATH, "mhp_clean.geojson"))

# A little cleansing
mhp = mhp.replace({"NOT AVAILABLE": pd.NA})

#%%

df = gpd.GeoDataFrame().assign(
    source_system_id    = mhp["mhp_id"],
    source_system       = "mhp",
    contributor_id      = "mhp." + mhp["mhp_id"],
    master_key          = "UNK-mhp." + mhp["mhp_id"],
    name                = mhp["mhp_name"],
    address_line_1      = mhp["address"],
    city                = mhp["city"],
    state               = mhp["state"],
    zip                 = mhp["zipcode"],
    county              = mhp["county"],
    geometry_lat        = mhp["latitude"],
    geometry_long       = mhp["longitude"],
    geometry            = mhp["geometry"],
    geometry_quality    = mhp["val_method"]
)

#%%

helpers.load_to_postgis("mhp", df)