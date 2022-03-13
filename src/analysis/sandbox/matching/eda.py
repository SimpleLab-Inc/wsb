"""
Splitting off the EDA portions of the SuperJoin to keep things cleaner, but maintain a history.
"""

#%%

import os
import pandas as pd
import geopandas as gpd
from dotenv import load_dotenv

load_dotenv()

pd.options.display.max_columns = None

DATA_PATH = os.environ["WSB_STAGING_PATH"]
EPSG = os.environ["WSB_EPSG"]

# Bring in the FIPS -> State Abbr crosswalk
crosswalk = (pd.read_csv("../crosswalks/state_fips_to_abbr.csv")
    .set_index("code"))

"""
Data Sources:
1. SDWIS - Official list of PWS's to classify. Narrow to Active CWS's.
2. FRS - Has centroids for ~15k facilities, but is largely redundant with ECHO.
3. ECHO? - Similar to FRS. Better matching. The points might be a superset of FRS.
4. TIGER - Generic city boundaries. Attempt to match on city name.
5. Mobile Home Parks - 
6. Various exact geometries from states

Possible other data sets:
- Facility Addresses from FRS or Echo (in addition to the primary PWS address which we already bring in)

"""

#%% ##########################################
# 1) SDWIS
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
ws.primacy_agency_code - Code for the state or territory with regulatory oversight
ws.population_served - Estimated number of people served. 0 or 1 might represent a wholesaler.
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

sdwis_unfiltered = pd.read_csv(
    DATA_PATH + "/sdwis_water_system.csv",
    usecols=keep_columns,
    dtype="string")


# Filter to only active community water systems
# Starts as 400k, drops to ~50k after this filter
sdwis = (
    sdwis_unfiltered.loc[
        (sdwis_unfiltered["pws_activity_code"].isin(["A"])) &
        (sdwis_unfiltered["pws_type_code"] == "CWS")])


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

"""
# Supplement with water_system_facilities?
# This would roughly denormalize by 10x...probably don't want to do that yet.

# Are facility addresses going to be a useful dataset? We could get from Echo or SDWIS

# water_system_facilities - PWSID + facility_id is unique
# There are ~300 PWSID's in water_system but not water_system_facilities
sdwis_wsf = pd.read_csv(DATA_PATH + "/sdwis_water_system_facility.csv")

# Filter to only pws's that we're interested in
sdwis_wsf = sdwis_wsf.loc[sdwis_wsf["pwsid"].isin(sdwis["pwsid"])]

sdwis_wsf.head()
"""

#%% ##########################################
# 2) FRS (EPA "Facility Registry Service")
# FRS data model: https://www.epa.gov/frs/frs-physical-data-model
##############################################

"""
Useful columns:
pgm_sys_id - 
    This is pretty much the primary key. (69,697 unique / 69,722 total). Dupes might be inactives
    The key varies based on INTEREST_TYPE:
    - When INTEREST_TYPE is "WATER TREATMENT PLANT" it's a pwsid + " " + facility_id
    - For all others, it appears to be a pwsid
active_status - 55k are "ACTIVE". Others have "INACTIVE", "CHANGED TO NON-PUBLIC SYSTEM", OR N/A
state_code - The state in which the facility is located
latitude83 - Lat of the facility
longitude83 - Long of the facility
accuracy_value - Measure of accuracy (in meters) of the lat/long
collect_mth_desc - Text describing how lat/long was calculated
ref_point_desc - Name that identifies the place for which geographic coordinates were established.
"""

frs = gpd.read_file(
    DATA_PATH + "/frs.geojson")

# keep_columns = [
#     "PGM_SYS_ID", "LATITUDE83", "LONGITUDE83", "ACCURACY_VALUE", 
#     "COLLECT_MTH_DESC", "REF_POINT_DESC", "geometry"]
#
#frs = frs[keep_columns]

#%%

# Assumption: PGM_SYS_ID is concatenated IFF INTEREST_TYPE == "WATER TREATMENT PLANT"
if (~(frs["interest_type"] == "WATER TREATMENT PLANT") == (frs["pgm_sys_id"].str.contains(" "))).any():
    raise Exception("Failed assumption: pgm_sys_id is concatenated IFF interest_type == 'WATER TREATMENT PLANT'")

print(f"Unique pwsid's: {len(frs['pwsid'].unique())}")

# 32,329 unique pwsid's after splitting apart the key.
# We'll either need to join to water_system_facilities for water treatment plants,
# Or we'll need to somehow aggregate the geometries
frs.head()

#%%
# Almost every pwsid matches to the unfiltered sdwis list
frs["pwsid"].isin(sdwis_unfiltered["pwsid"]).value_counts()

#%%
# But only 18k are CWS. Another 14k are non-community (TNCWS or NTNCWS)
sdwis_unfiltered[sdwis_unfiltered["pwsid"].isin(frs["pwsid"])]["pws_type_code"].value_counts()

#%%
# Only 16k distinct matches are active CWS
frs["matched"] = frs["pwsid"].isin(sdwis["pwsid"])
len(frs[frs["matched"]]["pwsid"].unique())

# 16k matches is far short of 50k matches.
# But I went back to the raw FRS data and couldn't find any additional matches.

# Since we successfully matched almost all FRS to unfiltered sdwis, it's not a matching problem.
# Instead, it's an FRS problem. FRS simply appears to lack many pwsid's.

# Options:
#  - echo_exporter dataset instead. That had better lat/long

#%%
# Filter to only those that have a match on pwsid. 
# 45k entries, but many are duplicated on facility_id
frs = frs[frs["matched"]].drop(columns=["matched"])

#%% ##########################################
# 3) TIGER
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
# 6) ECHO
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
# 53,500 SDWIS match to ECHO, 2209 don't match
echo_df = echo_df.loc[
    echo_df["pwsid"].isin(sdwis["pwsid"]) &
    echo_df["fac_lat"].notna()].copy()

# Convert to geopandas
echo: gpd.GeoDataFrame = gpd.GeoDataFrame(
    echo_df,
    geometry=gpd.points_from_xy(echo_df["fac_long"], echo_df["fac_lat"]),
    crs="EPSG:4326")

echo.head()


#%%
# Are there any patterns when echo is in FRS vs when it's not in FRS?

print("In FRS:")
print(echo[echo["pwsid"].isin(frs["pwsid"])]["fac_collection_method"].value_counts())

print("\nNot in FRS:")
print(echo[~echo["pwsid"].isin(frs["pwsid"])]["fac_collection_method"].value_counts())

# Yeah, interesting...
# When it matches FRS:
#  - fac_collection_method - Primarily "ADDRESS MATCHING-HOUSE NUMBER", "INTERPOLATION-PHOTO", "INTERPOLATION-MAP", etc.
#  - fac_reference_point - Detailed info about the specific reference point where the centroid was picked at the facility
# When it doesn't match FRS:
#  - fac_collection_method - Primarily "County Centroid", "Zip Code Centroid", "State Centroid". Yuck.
#  - fac_reference_point - Mostly null.


#%%
# Are all FRS attributes just a subset of ECHO?
# Hypothesis: FRS names, addresses, and lat/long match echo 100% when interest_type = "CWS"
# So FRS only provides additional value when interest_type = "WATER TREATMENT PLANT"

join = frs.merge(echo, on="pwsid")

latdiff = (join["fac_lat"] != join["latitude83"]) | (join["fac_long"] != join["longitude83"])
namediff = (join["primary_name"] != join["fac_name"])
addrdiff = (join["location_address"] != join["fac_street"]) | (join["city_name"] != join["fac_city"]) | (join["postal_code"] != join["fac_zip"])

#%%
# Yup - Almost all that have a name or lat/long diff are "Water Treatment Plant"
join[latdiff | namediff]["interest_type"].value_counts()

#%%
# But there are lots more address diffs because we've got multiple facilities
join[addrdiff]["interest_type"].value_counts()


#%% ##########################################
# 6) UCMR
##############################################

# 24,180 links from pwsid to zipcode
# pwsid, zipcode is _almost_ the PK. 5 duplicates
# 7,069 distinct pwsids

# Research:
# - [ ] Why are there 5 dupes on pwsid + zip?
# - [ ] Why are there a bunch where geometry is empty?
# - [ ] Could we get state code and county as columns in this file?

df = gpd.read_file(DATA_PATH + "/ucmr.geojson")

#%%
# Remove empty geometries
df = df[(~df["geometry"].is_empty) & df["geometry"].notna()]

#%%
# Aggregate polygons so pwsid is unique
df = df[["pwsid", "geometry"]].dissolve(by="pwsid")

#%%
df.head()

#%%

