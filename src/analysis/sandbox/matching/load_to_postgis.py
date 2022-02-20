"""
Clean up all these layers and save to PostGIS for efficient visualization in QGIS.
"""

#%%
import os
import pandas as pd
import geopandas as gpd
import sqlalchemy as sa
from dotenv import load_dotenv

load_dotenv()

pd.options.display.max_columns = None

data_path = os.environ["WSB_STAGING_PATH"]
SRC_EPSG = os.environ["WSB_EPSG"]

# Bring in the FIPS -> State Abbr crosswalk
crosswalk = (pd.read_csv("../crosswalks/state_fips_to_abbr.csv")
    .set_index("code"))

# Connect to local PostGIS instance
conn = sa.create_engine("postgresql://postgres:postgres@localhost:5434/sl_gis")

TGT_EPSG = 4326

#%%

# SDWIS doesn't have any geometry, but we use it to filter on the PWSID's of interest.
sdwis = pd.read_csv(
    data_path + "/sdwis_water_system.csv",
    usecols=["pwsid", "pws_activity_code", "pws_type_code"],
    dtype="str")


# Filter to only active community water systems
# Starts as 400k, drops to ~50k after this filter
sdwis = (
    sdwis.loc[
        (sdwis["pws_activity_code"].isin(["A", "N", "P"])) &
        (sdwis["pws_type_code"] == "CWS")]
    )["pwsid"]

#%%

frs = gpd.read_file(
    data_path + "/frs.geojson")

frs = frs.set_crs(SRC_EPSG, allow_override=True)

# Standardize columns to lowercase
frs.columns = [c.lower() for c in frs.columns]

# Add pwsid and facility_id columns by parsing apart the pgm_sys_id
frs = frs.join(frs["pgm_sys_id"]
    .str.extract(r"(\w+)(?: (\w+))?")
    .rename(columns={
        0: "pwsid",
        1: "facility_id" #type:ignore
    }))

# Filter to only those in SDWIS
frs = frs[frs["pwsid"].isin(sdwis)]

#%%
##############################################
# 3) TIGRIS
##############################################
tigris = gpd.read_file(data_path + "/tigris_places_clean.geojson")

tigris = tigris.set_crs(SRC_EPSG, allow_override=True)

# Make columns lower-case
tigris.columns = [c.lower() for c in tigris.columns]

# Standardize data type
tigris["statefp"] = tigris["statefp"].astype("int")

# Augment with state abbrev
tigris = tigris.join(crosswalk, on="statefp", how="inner")

#%%
##############################################
# 4) Labeled boundaries - What are these?
##############################################
wsb = gpd.read_file(data_path + "/wsb_labeled.geojson")
wsb = wsb.set_crs(SRC_EPSG, allow_override=True)

# Does this have both points and areas?

#%%
##############################################
# 5) Mobile Home Parks
##############################################
mhp = gpd.read_file(data_path + "/mhp_clean.geojson")


#%%
##############################################
# 6) Echo
##############################################

echo = pd.read_csv(
    data_path + "/../downloads/echo/ECHO_EXPORTER.csv",
    usecols=["SDWA_IDS", "FAC_LAT", "FAC_LONG", "FAC_NAME"],
    dtype="string")

# Standardize to lower case
echo.columns = [c.lower() for c in echo.columns]

# Filter to only those with sdwa_ids and lat/long
echo = echo.loc[echo["sdwa_ids"].notna() & echo["fac_lat"].notna()].copy()

# The sdwa_ids column contains multiple space-delimited PWSIDs. Turn them into Python lists.
echo["sdwa_ids"] = echo["sdwa_ids"].str.split()

# Now duplicate rows where we have multiple ID's and rename to pwsid
echo = echo.explode("sdwa_ids").rename(columns={"sdwa_ids": "pwsid"})

# Filter to the pws's of interest
echo = echo.loc[echo["pwsid"].isin(sdwis)]

# Convert to geopandas
echo = gpd.GeoDataFrame(
    echo,
    geometry=gpd.points_from_xy(echo["fac_long"], echo["fac_lat"]))


#%%
##############################################
# 10a) Oklahoma
##############################################

# How to read the RDS? Why converted to diff format instead of sticking with geojson?
# Going with raw instead.
ok = gpd.read_file(data_path + "/../downloads/boundary/ok/ok.geojson")


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
conn.execute("DROP TABLE IF EXISTS echo_export;")
echo.to_postgis("echo_export", conn, if_exists="append")
print("done.")

#%%
# OK
print("Loading OK...")
conn.execute("DROP TABLE IF EXISTS state_ok;")
ok.to_postgis("state_ok", conn, if_exists="append")
print("done.")
