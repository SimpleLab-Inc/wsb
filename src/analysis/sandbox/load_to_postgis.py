"""
If you like using the PostGIS database, say, to back a fast
ArcGIS map, use this script to convert our geojson files to
PostGIS tables.
"""

#%%

import pandas as pd
import geopandas as gpd
import os
import sqlalchemy as sa
from shapely.geometry import Polygon

from dotenv import load_dotenv

load_dotenv()

STAGING_PATH = os.environ["WSB_STAGING_PATH"]
OUTPUT_PATH = os.environ["WSB_OUTPUTS_PATH"]

# Connect to local PostGIS instance
conn = sa.create_engine(os.environ["POSTGIS_CONN_STR"])

#%% ##########################
# Echo
##############################

# Read file
df = gpd.read_file(STAGING_PATH + "/echo.geojson")

# Fill NA geometries with empty polygons
df["geometry"] = df["geometry"].fillna(Polygon([]))

# Save to DB
df.to_postgis("echo", conn, index=False, if_exists="replace")

#%% ##########################
# FRS
##############################

# Read file
df = gpd.read_file(STAGING_PATH + "/frs.geojson")

# Fill NA geometries with empty polygons
df["geometry"] = df["geometry"].fillna(Polygon([]))

# Save to DB
df.to_postgis("frs", conn, index=False, if_exists="replace")

#%% ##########################
# MHP
##############################

# Read file
df = gpd.read_file(STAGING_PATH + "/mhp_clean.geojson")

# Fill NA geometries with empty polygons
df["geometry"] = df["geometry"].fillna(Polygon([]))

# Save to DB
df.to_postgis("mhp", conn, index=False, if_exists="replace")


#%% ##########################
# UCMR
##############################

# Read file
df = pd.read_csv(STAGING_PATH + "/ucmr.csv")

# Add geometry column
df = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df["centroid_long"], df["centroid_lat"]),
    crs="EPSG:4326")

# Save to DB
df.to_postgis("ucmr", conn, index=False, if_exists="replace")

#%% ##########################
# TIGER
##############################

# Read file
df = gpd.read_file(STAGING_PATH + "/tigris_places_clean.geojson")

# Save to DB
df.to_postgis("tiger", conn, index=False, if_exists="replace")

#%% ##########################
# LABELED
##############################

# Read file
df = gpd.read_file(STAGING_PATH + "/wsb_labeled_clean.geojson")

# Save to DB
df.to_postgis("labeled", conn, index=False, if_exists="replace")

#%% ##########################
# TEMM
##############################

# Read file
df = gpd.read_file(OUTPUT_PATH + "/temm_layer/temm.geojson")

# Save to DB
df.to_postgis("temm", conn, index=False, if_exists="replace")
# %%
