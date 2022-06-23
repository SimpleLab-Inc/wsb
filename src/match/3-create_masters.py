"""
This script takes attributes from SDWIS, Echo, UCMR, and MHP
and combines the best info to create a "master record"
for each PWSID.
"""

#%%

import os
import numpy as np
import pandas as pd
import geopandas as gpd
import sqlalchemy as sa
from shapely.geometry import Polygon
from dotenv import load_dotenv

import match.helpers as helpers

load_dotenv()

STAGING_PATH = os.environ["WSB_STAGING_PATH"]
EPSG = os.environ["WSB_EPSG"]
PROJ = os.environ["WSB_EPSG_AW"]

# Connect to local PostGIS instance
conn = sa.create_engine(os.environ["POSTGIS_CONN_STR"])


#%%
# Load up the data sources

print("Pulling in data from database...", end="")

supermodel = gpd.GeoDataFrame.from_postgis("""
    SELECT *
    FROM pws_contributors
    WHERE source_system IN ('sdwis', 'echo', 'ucmr', 'mhp');""",
    conn, geom_col="geometry")

print("done.")

# Fix a few data types
supermodel["population_served_count"] = supermodel["population_served_count"].astype(pd.Int64Dtype())
supermodel["service_connections_count"] = supermodel["service_connections_count"].astype(pd.Int64Dtype())

sdwis = supermodel[supermodel["source_system"] == "sdwis"]
echo = supermodel[supermodel["source_system"] == "echo"]
ucmr = supermodel[supermodel["source_system"] == "ucmr"]
mhp = supermodel[supermodel["source_system"] == "mhp"].set_index("contributor_id")

#%%
matches = pd.read_sql("""
    SELECT
        m.master_key,
        m.candidate_contributor_id,
        m.match_rule,
        c.source_system_id
    FROM matches m
    JOIN pws_contributors c ON m.candidate_contributor_id = c.contributor_id
    WHERE c.source_system = 'mhp';
    """, conn)

print("Read matches from database.")

#%% ###########################
# Pick the best MHP match
###############################

# Sort by rank, then take the first one
# The best MHP match is selected arbitrarily (ie: by min candidate contributor id)
# This is fine, because multiple MHP matches are rare.
best_match = (matches
    .sort_values(["master_key", "candidate_contributor_id"])
    .drop_duplicates(subset=["master_key"], keep="first")
    [["master_key", "candidate_contributor_id", "source_system_id"]])

mhp_best_match = (best_match
    .join(mhp[["centroid_lat", "centroid_lon", "centroid_quality"]], on="candidate_contributor_id")
    .rename(columns={
        "source_system_id": "mhp_match_id",
        "centroid_lat": "mhp_lat",
        "centroid_lon": "mhp_lon",
        "centroid_quality": "mhp_quality"
    })
    .set_index("master_key")
    [["mhp_match_id", "mhp_lat", "mhp_lon", "mhp_quality"]])

print("Pulled useful information for the best MHP match.")


#%% ##########################
# Generate the final table
##############################

# Start with SDWIS as the base, but drop/override a few columns
output = (sdwis
    .drop(columns=["centroid_lat", "centroid_lon", "centroid_quality"])
    .assign(
        contributor_id             = "master." + sdwis["pwsid"],
        source_system              = "master",
        source_system_id           = sdwis["pwsid"],
        master_key                 = sdwis["pwsid"],
    ))


# Supplement with echo centroid
output = (output
    .merge(echo[[
        "pwsid",
        "centroid_lat",
        "centroid_lon",
        "centroid_quality",
    ]], on="pwsid", how="left"))

# If the PWS has a UCMR, and the echo quality is state or county centroid,
# overwrite the lat/long

output = (output
    .merge(
        ucmr[["pwsid", "centroid_lat", "centroid_lon", "centroid_quality"]]
        .rename(columns={
            "centroid_lat": "ucmr_lat",
            "centroid_lon": "ucmr_lon",
            "centroid_quality": "ucmr_quality"}),
        on="pwsid", how="left"))

mask = (
    output["centroid_quality"].isin(["STATE CENTROID", "COUNTY CENTROID"]) &
    output["ucmr_lat"].notna())

output.loc[mask, "centroid_lat"] = output[mask]["ucmr_lat"]
output.loc[mask, "centroid_lon"] = output[mask]["ucmr_lon"]
output.loc[mask, "centroid_quality"] = output[mask]["ucmr_quality"]

# If there's an MHP match, add matched ID and overwrite the lat/long
output = output.join(mhp_best_match, on="pwsid", how="left")

mask = output["mhp_match_id"].notna()
output.loc[mask, "centroid_lat"] = output[mask]["mhp_lat"]
output.loc[mask, "centroid_lon"] = output[mask]["mhp_lon"]
output.loc[mask, "centroid_quality"] = output[mask]["mhp_quality"]

# Verify: We should still have exactly the number of pwsid's as we started with
if not (len(output) == len(sdwis)):
    raise Exception("Output was filtered or denormalized")

print("Joined several data sources into final output.")


#%%
# A little cleanup
output = output.drop(columns=[
    "ucmr_lat", "ucmr_lon", "ucmr_quality",
    "mhp_lat", "mhp_lon", "mhp_quality", "mhp_match_id"])

#%%
output = gpd.GeoDataFrame(output)
output["geometry"] = Polygon([])
output = output.set_crs(epsg=EPSG, allow_override=True)

#%% ########################
# Save back to the DB
############################

helpers.load_to_postgis("master", output)