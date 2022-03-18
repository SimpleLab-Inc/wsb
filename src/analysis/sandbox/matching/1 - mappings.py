#%%

import os
from shapely.geometry import Polygon
import pandas as pd
import geopandas as gpd
from dotenv import load_dotenv
import sqlalchemy as sa

load_dotenv()

pd.options.display.max_columns = None

DATA_PATH = os.environ["WSB_STAGING_PATH"]
OUTPUT_PATH = os.path.join(DATA_PATH, "..", "outputs")
EPSG = os.environ["WSB_EPSG"]

# Bring in the FIPS -> State Abbr crosswalk
crosswalk = (pd.read_csv("../crosswalks/state_fips_to_abbr.csv")
    .set_index("code"))

"""
Data Sources:
1. SDWIS - Official list of PWS's to classify. Narrow to Active CWS's.
2. FRS - Has centroids for ~15k facilities.
3. ECHO? - Similar to FRS. Better matching. The points might be a superset of FRS.
4. tiger - Generic city boundaries. Attempt to match on city name.
5. Mobile Home Parks - 
6. Various exact geometries from states
"""

#%% ##########################################
# SDWIS
##############################################

"""
# SDWIS Schema

Table relationships:
- water_system
- water_system : water_system_facility is 1 : 0/N (~300 pwsid's missing, N=9.8 mean (wow!))
- water_system : service_area is 1 : 0/N, but almost 1:N (~1k pwsid's missing, N=1.2 mean)
- water_system : geographic_area is 1 : 0/1, but almost 1:1 (~1k pwsid's missing)

Here are the useful columns we want from SDWIS and supplemental tables
ws.pwsid - the PK
ws.pws_name - name
ws.pws_activity_code - active or not
ws.pws_type_code - Filtered to "cws" only so maybe we don't need it
ws.address_line1 - "The address applicable to the legal entity", whatever that means
ws.address_line2
ws.city_name
ws.zip_code
ws.primacy_agency_code
wsf.facility_id - Optional. This denormalizes the data substantially.
sa.service_area_type_code - for municipal vs mobile home park
ga.city_served - this column is not populated in ws unfortunately
ga.county_served - Maybe this will be helpful?
"""

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
# Keep only "A" for active
sdwis = sdwis.loc[
    (sdwis["pws_activity_code"].isin(["A"])) &
    (sdwis["pws_type_code"] == "CWS")]

# If state_code is NA, copy from primacy_agency_code
mask = sdwis["state_code"].isna()
sdwis.loc[mask, "state_code"] = sdwis.loc[mask, "primacy_agency_code"]


#########
# Supplement with geographic_area

# geographic_area - PWSID is unique, very nearly 1:1 with water_system
# ~1k PWSID's appear in water_system but not geographic_area
# We're trying to get city_served and county_served, but these columns aren't always populated
sdwis_ga = pd.read_csv(
    DATA_PATH + "/sdwis_geographic_area.csv",
    usecols=["pwsid", "city_served", "county_served"],
    dtype="string")

# Verify: pwsid is unique
if not sdwis_ga["pwsid"].is_unique:
    raise Exception("Failed assumption: pwsid in geographic_area is assumed to be unique")

sdwis = sdwis.merge(sdwis_ga, on="pwsid", how="left")

#########
# Supplement with service_area

# This is N:1 with sdwis, which is annoying
# (each pws has on average 1.2 service_area_type_codes)

# service_area - PWSID + service_area_type_code is unique
# ~1k PWSID's appear in water_system but not service_area
sdwis_sa = pd.read_csv(
    DATA_PATH + "/sdwis_service_area.csv",
    usecols=["pwsid", "service_area_type_code"])

# Filter to the pws's we're interested in
sdwis_sa = sdwis_sa.loc[sdwis_sa["pwsid"].isin(sdwis["pwsid"])]

# Supplement sdwis. I'll group it into a python list to avoid denormalized
# Could also do a comma-delimited string. We'll see what seems more useful in practice.
sdwis_sa = sdwis_sa.groupby("pwsid")["service_area_type_code"].apply(list)

sdwis = sdwis.merge(sdwis_sa, on="pwsid", how="left")

# Verification
if not sdwis["pwsid"].is_unique:
    raise Exception("Expected sdwis pwsid to be unique")

sdwis.head()


#%% ##########################################
# TIGER
##############################################
tiger = gpd.read_file(DATA_PATH + "/tigris_places_clean.geojson")

# keep_columns = ["STATEFP", "GEOID", "NAME", "NAMELSAD"]
# tiger = tiger[keep_columns]

# Standardize data type
tiger["statefp"] = tiger["statefp"].astype("int")

# Augment with state abbrev
tiger = tiger.join(crosswalk, on="statefp", how="inner")

# GEOID seems to be a safe unique identifier
tiger.head()

#%% ##########################################
# ECHO
##############################################

echo_df = pd.read_csv(
    DATA_PATH + "/echo.csv",
    usecols=[
        "pwsid", "fac_lat", "fac_long", "fac_name",
        "fac_street", "fac_city", "fac_state", "fac_zip", "fac_county", 
        'fac_collection_method', 'fac_reference_point', 'fac_accuracy_meters', 
        'fac_indian_cntry_flg', 'fac_percent_minority', 'fac_pop_den', 'ejscreen_flag_us'],
    dtype="string")

# Filter to only those in our SDWIS list and with lat/long
# 47,951 SDWIS match to ECHO, 1494 don't match
echo_df = echo_df.loc[
    echo_df["pwsid"].isin(sdwis["pwsid"]) &
    echo_df["fac_lat"].notna()].copy()

# If fac_state is NA, copy from pwsid
mask = echo_df["fac_state"].isna()
echo_df.loc[mask, "fac_state"] = echo_df.loc[mask, "pwsid"].str[0:2]

# Convert to geopandas
echo: gpd.GeoDataFrame = gpd.GeoDataFrame(
    echo_df,
    geometry=gpd.points_from_xy(echo_df["fac_long"], echo_df["fac_lat"]),
    crs="EPSG:4326")

# Cleanse out "UNK"
echo = echo.replace({"UNK": pd.NA})

echo.head()

#%% ##########################################
# FRS
##############################################

frs = gpd.read_file(
    DATA_PATH + "/frs.geojson")

# Filter to those in SDWIS
# And only those with interest_type "WATER TREATMENT PLANT". Other interest types are already in Echo.
frs = frs[
    frs["pwsid"].isin(sdwis["pwsid"]) &
    (frs["interest_type"] == "WATER TREATMENT PLANT")]

# We only need a subset of the columns
keep_columns = [
    "registry_id", "pwsid", "state", "primary_name", "location_address",
    "city_name", "postal_code", "county_name",
    "latitude83", "longitude83", "geometry", "ref_point_desc"]

frs = frs[keep_columns]

# Exclude FRS that are identical to echo on name and lat/long.
# Maybe later, we also want to allow them through if they have different addresses.
frs = frs.loc[frs
    # Find matches to echo, then only include those from FRS that _didn't_ match
    .reset_index()
    .merge(echo,
        left_on=["pwsid", "primary_name", "latitude83", "longitude83"],
        right_on=["pwsid", "fac_name", "fac_lat", "fac_long"],
        how="outer", indicator=True)
    .query("_merge == 'left_only'")
    ["index"]
]

# Furthermore, drop entries where all the columns of interest are duplicated
frs = frs.drop_duplicates(subset=list(set(frs.columns) - set("registry_id")), keep="first")

print(f"{len(frs)} FRS entries remain after removing various duplicates")

#%% ##########################################
# UCMR
##############################################

# Primarily: This links pwsid to zip code.
# Primary Key: pwsid + zipcode (because pws's may serve more than one zip)

ucmr = gpd.read_file(DATA_PATH + "/ucmr.geojson")

# Remove empty geometries
ucmr = ucmr[(~ucmr["geometry"].is_empty) & ucmr["geometry"].notna()]

# Aggregate polygons so pwsid is unique
ucmr = (ucmr[["pwsid", "geometry"]]
    .dissolve(by="pwsid")
    .reset_index())

#%% ##########################################
# MHP
##############################################

mhp = gpd.read_file(DATA_PATH + "/mhp_clean.geojson")

# A little cleansing
mhp = mhp.replace({"NOT AVAILABLE": pd.NA})

#%% #############################
# Mapping to a standard model
#################################

"""
1) Map to a unified data model:
    - source system name
    - source system key
    - pwsid
    - name
    - city served?
    - lat?
    - long?
    - geometry? - Either multiple columns for different geometry quality, or smart survivorship
#Jess notes: retain a column for each geometry, and then a new column for the winning geom?
        - shape
        - point
        - zip centroid
        - geometry_quality - (Opt?) Notes about the quality; e.g. whether it came from a zip, from multiple points that were averaged, etc
"""


#%%
#jess note to ryan: do we want to retain the match_ids (e.g. tiger geoid, etc)?

#%%

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
    geometry             = Polygon([])           # Empty geometry. Could replace with a zip centroid.
)

echo_supermodel = gpd.GeoDataFrame().assign(
    source_system_id        = echo["pwsid"],
    source_system           = "echo",
    xref_id                 = "echo." + echo["pwsid"],
    master_key              = echo["pwsid"],
    pwsid                   = echo["pwsid"],
    state                   = echo["fac_state"],
    name                    = echo["fac_name"],
    address_line_1          = echo["fac_street"],
    city                    = echo["fac_city"],
    zip                     = echo["fac_zip"],
    geometry_lat            = echo["fac_lat"],
    geometry_long           = echo["fac_long"],
    geometry                = echo["geometry"],
    geometry_quality        = echo["fac_collection_method"],
)

frs_supermodel = gpd.GeoDataFrame().assign(
    source_system_id        = frs["pwsid"],
    source_system           = "frs",
    xref_id                 = "frs." + frs["registry_id"] + "." + frs["pwsid"], # Apparently neither registry_id nor pwsid is fully unique, but together they are
    master_key              = frs["pwsid"],
    pwsid                   = frs["pwsid"],
    state                   = frs["state"],
    name                    = frs["primary_name"],
    address_line_1          = frs["location_address"],
    city                    = frs["city_name"],
    zip                     = frs["postal_code"],
    county                  = frs["county_name"],
    geometry_lat            = frs["latitude83"], # May need to convert CRS to make meaningful. Maybe in transformer?
    geometry_long           = frs["longitude83"],
    geometry                = frs["geometry"],
    geometry_quality        = frs["ref_point_desc"],
)

tiger_supermodel = gpd.GeoDataFrame().assign(
    source_system_id    = tiger["geoid"],
    source_system       = "tiger",
    xref_id             = "tiger." + tiger["geoid"],
    master_key          = pd.NA,
    name                = tiger["name"],
    state               = tiger["state"],
    geometry            = tiger["geometry"],
    geometry_quality    = "Tiger boundary"
)

ucmr_supermodel = gpd.GeoDataFrame().assign(
    source_system_id    = ucmr["pwsid"],
    source_system       = "ucmr",
    xref_id             = "ucmr." + ucmr["pwsid"],
    master_key          = ucmr["pwsid"],
    geometry            = ucmr["geometry"],
    geometry_quality    = "Zip code boundary"
)

mhp_supermodel = gpd.GeoDataFrame().assign(
    source_system_id    = mhp["mhp_id"],
    source_system       = "mhp",
    xref_id             = "mhp." + mhp["mhp_id"],
    master_key          = pd.NA,
    name                = mhp["mhp_name"],
    address_line_1      = mhp["address"],
    city                = mhp["city"],
    state               = mhp["state"],
    zip                 = mhp["zipcode"],
    county              = mhp["county"],
    geometry_lat        = mhp["latitude"],
    geometry_long       = mhp["longitude"],
    geometry            = mhp["geometry"],
    geometry_quality    = mhp["val_method"]
)

supermodel = pd.concat([
        sdwis_supermodel,
        echo_supermodel,
        frs_supermodel,
        ucmr_supermodel,
        tiger_supermodel,
        mhp_supermodel
    ],
    ignore_index=True)

# Reset the CRS - it gets lost in the concat (maybe because sdwis has no CRS)
supermodel = supermodel.set_crs(epsg=EPSG, allow_override=True)

# Assign missing master keys as "UNK-"
mask = supermodel["master_key"].isna()
supermodel.loc[mask, "master_key"] = "UNK-" + supermodel.loc[mask].index.astype("str")

#####################
# Cleansing

# More cleansing on the unified model
supermodel["zip"] = supermodel["zip"].str[0:5]
supermodel["name"] = supermodel["name"].str.upper()
supermodel["address_line_1"] = supermodel["address_line_1"].str.upper()
supermodel["address_line_2"] = supermodel["address_line_2"].str.upper()
supermodel["city"] = supermodel["city"].str.upper()
supermodel["state"] = supermodel["state"].str.upper()
supermodel["county"] = supermodel["county"].str.upper()
supermodel["city_served"] = supermodel["city_served"].str.upper()

#####################
# Address Cleansing

# Null out zips "99999" - doesn't exist.
supermodel.loc[supermodel["zip"] == "99999", "zip"] = pd.NA

# Identify and remove administrative addresses
supermodel["address_quality"] = pd.NA

# Any that have "PO BOX" are admin and should be removed
PO_BOX_REGEX = r"^P[\. ]?O\b\.? *BOX +\d+$"

mask = supermodel["address_line_1"].fillna("").str.contains(PO_BOX_REGEX, regex=True)
supermodel.loc[mask, "address_quality"] = "PO BOX" # May standardize later
supermodel.loc[mask, "address_line_1"] = pd.NA

mask = supermodel["address_line_2"].fillna("").str.contains(PO_BOX_REGEX, regex=True)
supermodel.loc[mask, "address_quality"] = "PO BOX" # May standardize later
supermodel.loc[mask, "address_line_2"] = pd.NA

# If there's an address in line 2 but not line 1, move it
mask = supermodel["address_line_1"].isna() & supermodel["address_line_2"].notna()
supermodel.loc[mask, "address_line_1"] = supermodel.loc[mask, "address_line_2"]
supermodel.loc[mask, "address_line_2"] = pd.NA

supermodel.sample(10)

#%% ##############################
# Save to PostGIS
##################################

conn = sa.create_engine(os.environ["POSTGIS_CONN_STR"])
TARGET_TABLE = "utility_xref"

conn.execute(f"DELETE FROM {TARGET_TABLE};")

supermodel.to_postgis(TARGET_TABLE, conn, if_exists="append")

# %%
# Alternative: Save to file
#supermodel.to_csv(OUTPUT_PATH + "/supermodel.csv", index=False)
