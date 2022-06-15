#%%

import os
import numpy as np
import pandas as pd
import geopandas as gpd
import sqlalchemy as sa
from shapely.geometry import Polygon
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
t1 = gpd.GeoDataFrame.from_postgis("""
            SELECT pwsid, geometry
            FROM pws_contributors
            WHERE source_system = 'labeled';""",
        conn, geom_col="geometry")

print("Retrieved Tier 1: Labeled boundaries.")

# Tier 2: MATCHED TIGER Place boundaries
t2 = gpd.GeoDataFrame.from_postgis("""
        SELECT
            m.master_key        AS pwsid,
            t.source_system_id  AS tiger_match_geoid,
            t.name              AS tiger_name,
            t.geometry
        FROM tiger_best_match m
        JOIN pws_contributors t ON
            t.source_system = 'tiger' AND
            t.source_system_id = m.tiger_match_geoid""",
        conn, geom_col="geometry")

print("Retrieved Tier 2: Tiger boundaries.")

# Tier 3: MODELED boundaries - use median result geometry but bring in CIs
t3 = (gpd
    .read_file(os.path.join(STAGING_PATH, "tier3_median.geojson"))
    [["pwsid", ".pred_lower", ".pred", ".pred_upper", "geometry"]]
    .rename(columns={
        ".pred_lower": "pred_05",
        ".pred":       "pred_50",
        ".pred_upper": "pred_95"}))

print("Retrieved Tier 3: modeled boundaries.")

#%%

# Assign tier labels
geoid_counts = t2.groupby("tiger_match_geoid").size()
duplicated_geoid = geoid_counts[geoid_counts > 1].index

t1["tier"] = "Tier 1"
t2["tier"] = np.where(
    t2["tiger_match_geoid"].isin(duplicated_geoid), "Tier 2b", "Tier 2a")
t3["tier"] = "Tier 3"

#%%

# matched output and tier classification ----------------------------------

# columns to keep in final df
columns = [
    "pwsid", "name", "primacy_agency_code", "state", "city_served", 
    "county", "population_served_count", "service_connections_count", 
    "service_area_type_code", "owner_type_code", "geometry_lat", 
    "geometry_long", "geometry_quality",
    "is_wholesaler_ind", "primacy_type",
    "primary_source_code"]

# read and format matched output
print("Reading matched output...")

base = pd.read_sql(f"""
    SELECT {','.join(columns)}
    FROM pws_contributors
    WHERE source_system = 'master';""", conn)

# Backwards compatibility
base.rename(columns={
    "name": "pws_name",
    "state": "state_code",
    "county": "county_served"
})

print("done.\n")


#%%
# combine tiers -----------------------------------------------------------

# Combine geometries from Tiers 1-3
# Where we have duplicates, prefer Tier 1 > 2 > 3
combined = gpd.GeoDataFrame(pd
    .concat([t1, t2, t3])
    .sort_values(by="tier") #type:ignore
    .drop_duplicates(subset="pwsid", keep="first")
    [["pwsid", "tier", "geometry", "pred_05", "pred_50", "pred_95"]])

# Join again to get tiger info
# we do this to get tiger info for ALL tiers
combined = combined.merge(
    t2[["pwsid", "tiger_match_geoid", "tiger_name"]], on="pwsid", how="left")

# Fix data types
combined["tiger_match_geoid"] = combined["tiger_match_geoid"].astype(pd.Int64Dtype())

# Join to base
temm = gpd.GeoDataFrame(base.merge(combined, on="pwsid", how="left"))

# Where we don't have data from any tier, mark as tier "none"
# (lower case to differentiate from Python's None)
temm.loc[temm["tier"].isna(), "tier"] = "none"

# Verify - We should have the same number of rows in df and in temm
assert len(temm) == len(base)

print("Combined a spatial layer using best available tiered data.\n")


#%%
# write to multiple output formats ----------------------------------------

# SHP files can only have 10 character column names
renames = {
    "primacy_agency_code":       "primacy_ag",
    "city_served":               "city_serve",
    "county_served":             "cnty_serve",
    "population_served_count":   "ppln_serve",
    "service_connections_count": "srvc_conn",
    "service_area_type_code":    "srvc_area",
    "owner_type_code":           "owner_type",
    "geometry_lat":              "gmtry_lat",
    "geometry_long":             "gmtry_lon",
    "geometry_quality":          "gmtry_qual",
    "tiger_match_geoid":         "tgr_geoid",
    "is_wholesaler_ind":         "is_whlslr",
    "primacy_type":              "prmcy_type",
    "primary_source_code":       "prmry_src",
}

# paths to write
path_geojson  = os.path.join(OUTPUT_PATH, "temm_layer", "temm.geojson")
path_shp      = os.path.join(OUTPUT_PATH, "temm_layer", "shp", "temm.shp")
path_csv      = os.path.join(OUTPUT_PATH, "temm_layer", "temm.csv")

# create dirs
if not os.path.exists(os.path.join(OUTPUT_PATH, "temm_layer", "shp")):
    os.makedirs(os.path.join(OUTPUT_PATH, "temm_layer", "shp"))

# write geojson, shp, and csv
temm.to_file(path_geojson, driver="GeoJSON")
temm.rename(columns=renames).to_file(path_shp, driver="ESRI Shapefile")
temm.drop(columns="geometry").to_csv(path_csv)

print("Wrote data to geojson, shp, csv.\n\n\n")
