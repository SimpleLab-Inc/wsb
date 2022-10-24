#%%

import os
import pandas as pd
import geopandas as gpd
import sqlalchemy as sa
import match.helpers as helpers
from dotenv import load_dotenv
from shapely.geometry import Polygon

load_dotenv()

STAGING_PATH = os.environ["WSB_STAGING_PATH"]
OUTPUT_PATH = os.environ["WSB_OUTPUT_PATH"]
EPSG = os.environ["WSB_EPSG"]

# Connect to local PostGIS instance
conn = sa.create_engine(os.environ["POSTGIS_CONN_STR"])

#%%
# load geometries for each tier -------------------------------------------

print("Loading geometries for Tiers 1-3...") 

# Tier 1: LABELED (and CONTRIBUTED) boundaries
t1 = gpd.GeoDataFrame.from_postgis("""
            SELECT pwsid, centroid_lat, centroid_lon, centroid_quality, geometry
            FROM pws_contributors
            WHERE
                source_system IN ('labeled', 'contributed') AND
                NOT st_isempty(geometry)
            ORDER BY source_system, pwsid;""",
        conn, geom_col="geometry")

# If there are duplicates, it's likely because we have a contributed AND a labeled bound.
# Take only the contributed.
before_count = len(t1)
t1 = t1.drop_duplicates(subset="pwsid", keep="first")

if len(t1) < before_count:
    print(f"Prioritized {before_count - len(t1)} contributed record over labeled in T1.")

print("Retrieved Tier 1: Labeled boundaries.")

# Tier 2: MATCHED boundaries (only the best)
t2 = gpd.GeoDataFrame.from_postgis("""
            SELECT
                m.master_key        AS pwsid,
                t.source_system_id  AS matched_bound_geoid,
                t.name              AS matched_bound_name,
                t.centroid_lat,
                t.centroid_lon,
                t.centroid_quality,
                t.geometry
            FROM matches_ranked m
            JOIN pws_contributors t ON m.candidate_contributor_id = t.contributor_id
            WHERE
                m.best_match AND
                t.source_system = 'tiger'""",
        conn, geom_col="geometry")

print("Retrieved Tier 2: Matched boundaries.")

# Tier 3: MODELED boundaries - use median result geometry but bring in CIs
t3 = (gpd
    .read_file(os.path.join(STAGING_PATH, "tier3_median.gpkg"))
    [["pwsid", ".pred_lower", ".pred", ".pred_upper",
    "centroid_lat", "centroid_lon", "centroid_quality", "geometry"]]
    .rename(columns={
        ".pred_lower": "pred_05",
        ".pred":       "pred_50",
        ".pred_upper": "pred_95"}))

print("Retrieved Tier 3: Modeled boundaries.")

#%%

# Assign tier labels
t1["tier"] = 1
t2["tier"] = 2
t3["tier"] = 3

#%%
# Pull in base attributes from SDWIS ----------------------------------

# read and format matched output
print("Reading SDWIS for base attributes...")

base = pd.read_sql(f"""
    SELECT *
    FROM pws_contributors
    WHERE source_system = 'sdwis';""", conn)

base = base.drop(columns=["tier", "centroid_lat", "centroid_lon", "centroid_quality", "geometry"])

# Overwrite the contributor_id
base["contributor_id"] = "master." + base["pwsid"]
base["source_system"] = "master"

#%%
# combine tiers -----------------------------------------------------------

# Combine geometries from Tiers 1-3
# Where we have duplicates, prefer Tier 1 > 2 > 3
combined = gpd.GeoDataFrame(pd
    .concat([t1, t2, t3])
    .sort_values(by="tier") #type:ignore
    .drop_duplicates(subset="pwsid", keep="first")
    [["pwsid", "tier", "centroid_lat", "centroid_lon", "centroid_quality",
    "geometry", "pred_05", "pred_50", "pred_95"]])

# Join again to get matched boundary info
# we do this to get boundary info for ALL tiers
combined = combined.merge(
    t2[["pwsid", "matched_bound_geoid", "matched_bound_name"]], on="pwsid", how="left")

# Fix data types
combined["matched_bound_geoid"] = combined["matched_bound_geoid"].astype(pd.Int64Dtype())

# Join to base
temm = gpd.GeoDataFrame(
    base.merge(combined, on="pwsid", how="left"),
    crs=f"epsg:{EPSG}")

# Allow NA when we have no geometry
temm["tier"] = temm["tier"].astype(pd.Int64Dtype())

# Replace empty geometries
temm.loc[temm["geometry"].is_empty | temm["geometry"].isna(), "geometry"] = Polygon([]) #type:ignore

# Verify - We should have the same number of rows in df and in temm
assert len(temm) == len(base)

print("Combined a spatial layer using best available tiered data.\n")

#%%

# Save to the database
helpers.load_to_postgis("master",
    temm.drop(columns=["matched_bound_geoid", "matched_bound_name", "pred_05", "pred_50", "pred_95"]))

#%%
# Export

# The file outputs have a subset of columns
columns = [
    "pwsid", "name", "primacy_agency_code", "state", "city_served", 
    "county", "population_served_count", "service_connections_count", 
    "service_area_type_code", "owner_type_code",
    "is_wholesaler_ind", "primacy_type",
    "primary_source_code", "tier",
    "centroid_lat", "centroid_lon", "centroid_quality",
    "geometry", "pred_05", "pred_50", "pred_95"]

# Backwards compatibility
output = (temm[columns]
    .rename(columns={
        "name": "pws_name",
        "state": "state_code",
        "county": "county_served"
    }))

#%%
# paths to write
path_geopkg   = os.path.join(OUTPUT_PATH, "temm_layer", "temm.gpkg")
output.to_file(path_geopkg, driver="GPKG")

print("Wrote data to geopackage.\n")


#%%
# Export to additional formats

# SHP files can only have 10 character column names
renames = {
    "primacy_agency_code":       "primacy_ag",
    "city_served":               "city_serve",
    "county_served":             "cnty_serve",
    "population_served_count":   "ppln_serve",
    "service_connections_count": "srvc_conn",
    "service_area_type_code":    "srvc_area",
    "owner_type_code":           "owner_type",
    "centroid_lat":              "cntrd_lat",
    "centroid_lon":              "cntrd_lon",
    "centroid_quality":          "cntrd_qual",
    "matched_bound_geoid":       "bnd_geoid",
    "matched_bound_name":        "bnd_name",
    "is_wholesaler_ind":         "is_whlslr",
    "primacy_type":              "prmcy_type",
    "primary_source_code":       "prmry_src",
}

path_geojson  = os.path.join(OUTPUT_PATH, "temm_layer", "temm.geojson")
path_shp      = os.path.join(OUTPUT_PATH, "temm_layer", "shp", "temm.shp")
path_csv      = os.path.join(OUTPUT_PATH, "temm_layer", "temm.csv")

# create shapefile dir
if not os.path.exists(os.path.join(OUTPUT_PATH, "temm_layer", "shp")):
    os.makedirs(os.path.join(OUTPUT_PATH, "temm_layer", "shp"))

# write geojson, shp, and csv
output.to_file(path_geojson, driver="GeoJSON")
output.rename(columns=renames).to_file(path_shp, driver="ESRI Shapefile")
output.drop(columns="geometry").to_csv(path_csv)

print("Wrote data to geojson, shp, csv.\n\n\n")
