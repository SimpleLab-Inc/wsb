"""
Clean up all these layers and save to PostGIS for efficient visualization in QGIS.
"""

#%%
import os
import pandas as pd
import geopandas as gpd
import sqlalchemy as sa
from dotenv import load_dotenv
from shapely.geometry import Polygon

load_dotenv()

pd.options.display.max_columns = None

DATA_PATH = os.environ["WSB_STAGING_PATH"]
SRC_EPSG = os.environ["WSB_EPSG"]

# Bring in the FIPS -> State Abbr crosswalk
crosswalk = (pd.read_csv("../crosswalks/state_fips_to_abbr.csv")
    .set_index("code"))

# Connect to local PostGIS instance
conn = sa.create_engine("postgresql://postgres:postgres@localhost:5434/sl_gis")

TGT_EPSG = 4326

#%%

#%% ##########################################
# 1) SDWIS
##############################################

#########
# 1) SDWIS water_systems - PWSID is unique
keep_columns = ["pwsid", "pws_name", "pws_activity_code", "pws_type_code", "primacy_agency_code", 
    "address_line1", "address_line2", "city_name", "zip_code", "state_code",
    "population_served_count", "service_connections_count", "owner_type_code",
    "primacy_type"]

sdwis = pd.read_csv(
    DATA_PATH + "/sdwis_water_system.csv",
    usecols=keep_columns,
    dtype="string")


# Filter to only active community water systems
# Starts as 400k, drops to ~50k after this filter
sdwis = sdwis.loc[
    (sdwis["pws_activity_code"].isin(["A"])) &
    (sdwis["pws_type_code"] == "CWS")]

#########
# Supplement with geographic_area

# geographic_area - PWSID is unique, very nearly 1:1 with water_system
# ~1k PWSID's appear in water_system but not geographic_area
# We're trying to get city_served and county_served, but these columns aren't always populated
sdwis_ga = pd.read_csv(
    DATA_PATH + "/sdwis_geographic_area.csv",
    usecols=["pwsid", "city_served", "county_served"],
    dtype="string")

sdwis = sdwis.merge(sdwis_ga, on="pwsid", how="left")

#########
# Map to standard model

sdwis_supermodel = gpd.GeoDataFrame().assign(
    source_system_id     = sdwis["pwsid"],
    source_system        = "sdwis",
    xref_id              = "sdwis." + sdwis["pwsid"],
    master_key           = sdwis["pwsid"],
    pwsid                = sdwis["pwsid"],
    state                = sdwis["state_code"],
    name                 = sdwis["pws_name"],
    address_line_1       = sdwis["address_line1"],
    address_line_2       = sdwis["address_line2"],
    city                 = sdwis["city_name"],
    zip                  = sdwis["zip_code"],
    city_served          = sdwis["city_served"],
    geometry             = Polygon([]) # Empty geometry. Perhaps should fill with zip centroids instead? Admin address geocodes?
)

sdwis_supermodel = sdwis_supermodel.set_crs(epsg=4326, allow_override=True)


#%%
print("Loading sdwis...")
conn.execute("DELETE FROM utility_xref WHERE source_system = 'sdwis';")
sdwis_supermodel.to_postgis("utility_xref", conn, if_exists="append")
print("done.")


#%% ##########################################
# TIGER
##############################################
tigris = gpd.read_file(DATA_PATH + "/tigris_places_clean.geojson")

tigris = tigris.set_crs(SRC_EPSG, allow_override=True)

# Standardize data type
tigris["statefp"] = tigris["statefp"].astype("int")

# Augment with state abbrev
tigris = tigris.join(crosswalk, on="statefp", how="inner")

#%% ##########################################
# 4) Labeled boundaries - What are these?
##############################################
# wsb = gpd.read_file(data_path + "/wsb_labeled.geojson")
# wsb = wsb.set_crs(SRC_EPSG, allow_override=True)

# Does this have both points and areas?

#%% ##########################################
# Mobile Home Parks
##############################################
mhp = gpd.read_file(DATA_PATH + "/mhp_clean.geojson")


#%% ##########################################
# Echo
##############################################

echo = pd.read_csv(
    DATA_PATH + "/echo.csv",
    usecols=[
        "pwsid", "fac_lat", "fac_long", "fac_name",
        'fac_collection_method', 'fac_reference_point', 'fac_accuracy_meters'],
    dtype="str")

# Filter to only those in our SDWIS list and with lat/long
echo = echo.loc[
    echo["pwsid"].isin(sdwis) &
    echo["fac_lat"].notna()].copy()

# Convert to geopandas
echo = gpd.GeoDataFrame(
    echo,
    geometry=gpd.points_from_xy(echo["fac_long"], echo["fac_lat"]),
    crs="EPSG:4326")


#%% ##########################################
# Oklahoma
##############################################

# How to read the RDS? Why converted to diff format instead of sticking with geojson?
# Going with raw instead.
ok = gpd.read_file(DATA_PATH + "/../downloads/boundary/ok/ok.geojson")



#%% ##########################################
# FRS
##############################################

frs = gpd.read_file(
    DATA_PATH + "/frs.geojson")

frs = frs.set_crs(SRC_EPSG, allow_override=True)

# Filter to only those in SDWIS
frs = frs[frs["pwsid"].isin(sdwis)]

#%% ##############################
# Save layers to PostGIS
###################################

#%%
# tigris
print("Loading tigris...")
conn.execute("DROP TABLE IF EXISTS tigris;")
tigris.to_crs(epsg=TGT_EPSG).to_postgis("tigris", conn, if_exists="append")
print("done.")

#%%
# frs
print("Loading frs...")
conn.execute("DROP TABLE IF EXISTS frs;")
frs.to_crs(epsg=TGT_EPSG).to_postgis("frs", conn, if_exists="append")
print("done.")

#%%
# MHP
print("Loading MHP...")
conn.execute("DROP TABLE IF EXISTS mhp;")
mhp.to_crs(epsg=TGT_EPSG).to_postgis("mhp", conn, if_exists="append")
print("done.")

#%%
# ECHO
print("Loading echo...")
conn.execute("DROP TABLE IF EXISTS echo;")
echo.to_postgis("echo", conn, if_exists="append")
print("done.")

#%%
# OK
print("Loading OK...")
conn.execute("DROP TABLE IF EXISTS state_ok;")
ok.to_postgis("state_ok", conn, if_exists="append")
print("done.")
