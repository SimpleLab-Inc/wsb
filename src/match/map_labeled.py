#%%

import os
import pandas as pd
import geopandas as gpd
from dotenv import load_dotenv

import match.helpers as helpers

load_dotenv()

pd.options.display.max_columns = None

DATA_PATH = os.environ["WSB_STAGING_PATH"]
EPSG = os.environ["WSB_EPSG"]


#%%

labeled = gpd.read_file(os.path.join(DATA_PATH, "wsb_labeled_clean.geojson"))
print("Read Labeled WSB file.")

pwsids = helpers.get_pwsids_of_interest()
print("Retrieved PWSID's of interest.")

#%%
# Filter to those in SDWIS
labeled = labeled[labeled["pwsid"].isin(pwsids)]

#%%
# Null out a few bad lat/long
mask = (
    (labeled["centroid_lat"] < -90) | (labeled["centroid_lat"] > 90) |
    (labeled["centroid_long"] < -180) | (labeled["centroid_long"] > 180))

labeled.loc[mask, "centroid_lat"] = pd.NA
labeled.loc[mask, "centroid_long"] = pd.NA

print(f"Nulled out {mask.sum()} bad lat/long.")

#%%

df = gpd.GeoDataFrame().assign(
    source_system_id        = labeled["pwsid"],
    source_system           = "labeled",
    contributor_id          = "labeled." + labeled["pwsid"],
    master_key              = labeled["pwsid"],
    pwsid                   = labeled["pwsid"],
    state                   = labeled["state"],
    primacy_agency_code     = labeled["pwsid"].str[0:2],
    name                    = labeled["pws_name"],
#    address_line_1          = labeled["location_address"],
    city                    = labeled["city"],
#    zip                     = labeled["postal_code"],
    county                  = labeled["county"],
    # Need to convert these to EPSG:4326 before we can save them
    centroid_lat            = labeled["centroid_lat"],
    centroid_lon            = labeled["centroid_long"],
    geometry                = labeled["geometry"],
    centroid_quality        = "CALCULATED FROM GEOMETRY",
)

#%%

print("Labeled record counts:")
print(df
    .groupby("primacy_agency_code")
    .size()
    .sort_index())

# %%
helpers.load_to_postgis("labeled", df)