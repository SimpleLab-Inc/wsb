#%%

import os
import geopandas as gpd
import pandas as pd
from dotenv import load_dotenv
import match.helpers as helpers

load_dotenv()

DATA_PATH = os.environ["WSB_STAGING_PATH"]
EPSG = os.environ["WSB_EPSG"]

#%% 

ucmr = pd.read_csv(os.path.join(DATA_PATH, "ucmr.csv"))

ucmr = gpd.GeoDataFrame(
    ucmr,
    geometry=gpd.points_from_xy(ucmr["centroid_long"], ucmr["centroid_lat"]),
    crs="EPSG:4326")

print("Loaded UCMR")

pwsids = helpers.get_pwsids_of_interest()
ucmr = ucmr[ucmr["pwsid"].isin(pwsids)]
print("Filtered to PWSID's of interest.")

#%%

df = gpd.GeoDataFrame().assign(
    source_system_id    = ucmr["pwsid"],
    source_system       = "ucmr",
    contributor_id      = "ucmr." + ucmr["pwsid"],
    master_key          = ucmr["pwsid"],
    pwsid               = ucmr["pwsid"],
    zip                 = ucmr["zipcode"].str[0:5],
    centroid_lat        = ucmr["centroid_lat"],
    centroid_lon        = ucmr["centroid_long"],
    geometry            = ucmr["geometry"],
    centroid_quality    = "ZIP CODE CENTROID"
)

#%%

helpers.load_to_postgis("ucmr", df)