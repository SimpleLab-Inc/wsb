#%%

import os
import numpy as np
import pandas as pd
import geopandas as gpd
import sqlalchemy as sa
from dotenv import load_dotenv

load_dotenv()

STAGING_PATH = os.environ["WSB_STAGING_PATH"]
OUTPUT_PATH = os.environ["WSB_OUTPUT_PATH"]
EPSG = os.environ["WSB_EPSG"]
PROJ = os.environ["WSB_EPSG_AW"]

# Connect to local PostGIS instance
conn = sa.create_engine(os.environ["POSTGIS_CONN_STR"])

#%%
# load geometries for each tier -------------------------------------------

print("Loading geometries for Tiers 1-3...") 

# Tier 1: ASSIMILATED labeled boundaries
t1 = (gpd
    .read_file(os.path.join(STAGING_PATH, "wsb_labeled_clean.geojson"))
    [["pwsid", "geometry"]])

# Tier 2: MATCHED TIGER Place boundaries
t2 = (gpd
    .read_file(os.path.join(STAGING_PATH, "tigris_places_clean.geojson"))
    [["geoid", "name"]]
    .rename(columns={
        "geoid": "tiger_match_geoid",
        "name":  "tiger_name"})
    .astype({"tiger_match_geoid": "float64"}))

# Tier 3: MODELED boundaries - use median result geometry but bring in CIs
t3 = (gpd
    .read_file(os.path.join(STAGING_PATH, "tier3_median.geojson"))
    [["pwsid", ".pred_lower", ".pred", ".pred_upper", "geometry"]]
    .rename(columns={
        ".pred_lower": "pred_05",
        ".pred":       "pred_50",
        ".pred_upper": "pred_95"}))

print("done.\n") 

#%%

# matched output and tier classification ----------------------------------

# columns to keep in final df
keep_columns = [
    "pwsid", "pws_name", "primacy_agency_code", "state_code", "city_served", 
    "county_served", "population_served_count", "service_connections_count", 
    "service_area_type_code", "owner_type_code", "geometry_lat", 
    "geometry_long", "geometry_quality", "tiger_match_geoid", 
    "has_labeled_bound", "is_wholesaler_ind", "primacy_type",
    "primary_source_code", "tier"]

# read and format matched output
print("Reading matched output...")

df = pd.read_csv(os.path.join(STAGING_PATH, "matched_output.csv"))


df["tier"] = (
    np.where(df["has_labeled_bound"], "Tier 1",
    np.where(~df["has_labeled_bound"] & (df["tiger_to_pws_match_count"] == 1), "Tier 2a",
    np.where(~df["has_labeled_bound"] & (df["tiger_to_pws_match_count"] > 1), "Tier 2b",
    "Tier 3"))))

df = df[keep_columns]

print("done.\n") 

#%%
# combine tiers -----------------------------------------------------------

# Separate Tiers 1-3 from matched output, join to spatial data, and bind
dt1 = df[df["tier"] == "Tier 1"].merge(t1, on="pwsid")
dt2 = df[df["tier"].isin(["Tier 2a", "Tier 2b"])].merge(t2, on="tiger_match_geoid")
dt3 = df[df["tier"] == "Tier 3"].merge(t3, on="pwsid", how="left")

temm = gpd.GeoDataFrame(pd.concat([dt1, dt2, dt3]))

# Fix data types
temm["tiger_match_geoid"] = temm["tiger_match_geoid"].astype(pd.Int64Dtype())

print("Combined a spatial layer using best available tiered data.\n")


#%%
# write to multiple output formats ----------------------------------------

# paths to write
path_geojson  = os.path.join(OUTPUT_PATH, "temm_layer", "temm.geojson")
path_shp      = os.path.join(OUTPUT_PATH, "temm_layer", "shp", "temm.shp")
path_csv      = os.path.join(OUTPUT_PATH, "temm_layer", "temm.csv")

# create dirs
if not os.path.exists(os.path.join(OUTPUT_PATH, "temm_layer", "shp")):
    os.makedirs(os.path.join(OUTPUT_PATH, "temm_layer", "shp"))

# write geojson, shp, and csv
temm.to_file(path_geojson, driver="GeoJSON")
temm.to_file(path_shp, driver="ESRI Shapefile")
temm.drop(columns="geometry").to_csv(path_csv)

print("Wrote data to geojson, shp, csv.\n\n\n")
