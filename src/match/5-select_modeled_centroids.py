"""
This script takes centroids from ECHO, FRS, UCMR, and MHP
and tries to select the best one to feed into the model
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

sdwis = gpd.GeoDataFrame.from_postgis("""
    SELECT *
    FROM pws_contributors
    WHERE source_system = 'sdwis';""",
    conn, geom_col="geometry")

stack = pd.read_sql("""

    -- ECHO, FRS, and UCMR area all already-labeled with PWS
    SELECT
        c.contributor_id, c.source_system, c.master_key,
        c.centroid_lat, c.centroid_lon, c.centroid_quality,
        1 as master_group_ranking
    FROM pws_contributors c
    WHERE source_system IN ('echo', 'frs', 'ucmr')
    
    UNION ALL

    -- Since we don't know PWSID's for MHP and TIGER, we need
    -- to join to matches to sub in their matcheda MK's

    -- Join MHP to matches
    SELECT
        c.contributor_id, c.source_system, m.master_key,
        c.centroid_lat, c.centroid_lon, c.centroid_quality,
        1 as master_group_ranking
    FROM pws_contributors c
    JOIN matches m ON m.candidate_contributor_id = c.contributor_id
    WHERE source_system = 'mhp'

    UNION ALL

    -- Join Tiger to matches
    SELECT
        c.contributor_id, c.source_system, m.master_key,
        c.centroid_lat, c.centroid_lon, c.centroid_quality,
        -- This helps us decide the best tiger match
        m.master_group_ranking
    FROM pws_contributors c
    JOIN matches_ranked m ON m.candidate_contributor_id = c.contributor_id
    WHERE source_system = 'tiger'

    ORDER BY master_key;""",
    conn)

print("done.")

# Add sourcing notes to the geometries
stack["centroid_quality"] = stack["source_system"].str.upper() + ": " + stack["centroid_quality"]


#%% ###########################
# Find the best centroid from the candidate contributors
###############################

# Ranking:
#  Best MHP > 
#  Echo (if not state or county centroid) >
#  UCMR >
#  Boundary >
#  Echo (if state or county centroid)

# We want the best centroid from all contributors.
# Assign a ranking: 
# MHP = 1
# Echo = 2 if not state/county centroid
# FRS = 3
# UCMR = 4
# Boundary = 5
# Echo = 6 if state/county centroid 

stack["system_rank"] = stack["source_system"].map({
    "mhp": 1,
    "echo": 2,
    "frs": 3,
    "ucmr": 4,
    "tiger": 5
})

# Change Echo to 6 if state/county centroid
mask = (
    (stack["source_system"] == "echo") & 
    (stack["centroid_quality"].isin(["ECHO: STATE CENTROID", "ECHO: COUNTY CENTROID"])))

stack.loc[mask, "system_rank"] = 6

#%%
# In case there are multiple matches from the same system,
# we need tiebreakers.
# Go by:
# 1) System Ranking
# 2) match_rank
# 3) contributor_id (tiebreaker - to ensure consistency)

# Note that only MHP and Tiger could potentially have multiple matches

# Keep only the first entry in each subset
best_centroid = (stack
    .sort_values([
        "master_key",
        "system_rank",
        "master_group_ranking",
        "contributor_id"])
    .drop_duplicates(subset="master_key", keep="first")
    .set_index("master_key"))


#%% ##########################
# Generate the final table
##############################

# Start with SDWIS as the base, but drop/override a few columns
output = (sdwis
    .drop(columns=["centroid_lat", "centroid_lon", "centroid_quality"])
    .assign(
        contributor_id             = "modeled." + sdwis["pwsid"],
        source_system              = "modeled",
        source_system_id           = sdwis["pwsid"],
        master_key                 = sdwis["pwsid"],
        tier                       = 3,
        geometry_source_detail     = "Modeled"
    ))


# Supplement with best centroid
output = (output
    .merge(best_centroid[[
        "centroid_lat",
        "centroid_lon",
        "centroid_quality",
    ]], on="master_key", how="left"))

# Verify: We should still have exactly the number of pwsid's as we started with
if not (len(output) == len(sdwis)):
    raise Exception("Output was filtered or denormalized")

print("Joined several data sources into final output.")

#%%
output = gpd.GeoDataFrame(output)
output["geometry"] = Polygon([])
output = output.set_crs(epsg=EPSG, allow_override=True)

#%% ########################
# Save back to the DB
############################

helpers.load_to_postgis("modeled", output)