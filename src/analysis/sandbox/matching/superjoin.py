#%%

import os
import pandas as pd
import geopandas as gpd
from dotenv import load_dotenv

load_dotenv()

pd.options.display.max_columns = None

data_path = os.environ["WSB_STAGING_PATH"]
EPSG = os.environ["WSB_EPSG"]

# Bring in the FIPS -> State Abbr crosswalk
crosswalk = (pd.read_csv("../crosswalks/state_fips_to_abbr.csv")
    .set_index("code"))

"""
Data Sources:
1. SDWIS - Official list of PWS's to classify. Narrow to Active CWS's.
2. FRS - Has centroids for ~15k facilities.
3. ECHO? - Similar to FRS. Better matching. The points might be a superset of FRS.
4. TIGRIS - Generic city boundaries. Attempt to match on city name.
5. Mobile Home Parks - 
6. Various exact geometries from states
"""

# TODO - Chat with team
# - [ ] Some of this logic could be moved to the transformers
# - Share PostGIS database
# - Discuss standards:
#       - Why ESRI:102003 instead of EPSG:4326? Apparently geojson only allows 4326
#       - Let's unify the data formats. GeoJSON? Shared PostGIS DB? Shapefiles?
#       - Why's OK an RDS instead of a geojson?
# - What's "transform_wsb"? How's it differ from the separat MHP and OK transforms?
# - Only 16k matches to FRS. Should we look to Echo instead? Is that admin addresses?
# - Echo has much better matches, and seems to be a superset of FRS.

#%%
# Get clean versions of all the data sources.

##############################################
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
ws.primacy_agency_code
wsf.facility_id - Optional. This denormalizes the data substantially.
sa.service_area_type_code - for municipal vs mobile home park
ga.city_served - this column is not populated in ws unfortunately
ga.county_served - Maybe this will be helpful?
"""

# 1) SDWIS water_systems - PWSID is unique
keep_columns = ["pwsid", "pws_name", "address_line1", "address_line2", "city_name",
    "zip_code", "primacy_agency_code", "pws_activity_code", "pws_type_code"]

sdwis_unfiltered = pd.read_csv(
    data_path + "/sdwis_water_system.csv",
    usecols=keep_columns,
    dtype="string")


# Filter to only active community water systems
# Starts as 400k, drops to ~50k after this filter
sdwis = (
    sdwis_unfiltered.loc[
        (sdwis_unfiltered["pws_activity_code"].isin(["A", "N", "P"])) &
        (sdwis_unfiltered["pws_type_code"] == "CWS")])


# Supplement with geographic_area #########

# geographic_area - PWSID is unique, very nearly 1:1 with water_system
# ~1k PWSID's appear in water_system but not geographic_area
# We're trying to get city_served and county_served, but these columns aren't always populated
sdwis_ga = pd.read_csv(
    data_path + "/sdwis_geographic_area.csv",
    usecols=["pwsid", "city_served", "county_served"],
    dtype="string")

# Verify: pwsid is unique
if not sdwis_ga["pwsid"].is_unique:
    raise Exception("Failed assumption: pwsid in geographic_area is assumed to be unique")

sdwis = sdwis.merge(sdwis_ga, on="pwsid", how="left")

#%%

# Supplement with service_area? #########
# We don't want to do this just yet cause it will denormalize
# (each pws has on average 1.2 service_area_type_codes)

# service_area - PWSID + service_area_type_code is unique
# ~1k PWSID's appear in water_system but not service_area
sdwis_sa = pd.read_csv(
    data_path + "/sdwis_service_area.csv",
    usecols=["pwsid", "service_area_type_code"])

# Filter to the pws's we're interested in
sdwis_sa = sdwis_sa.loc[sdwis_sa["pwsid"].isin(sdwis["pwsid"])]

sdwis_sa.head()


#%%
# Supplement with water_system_facilities?
# This would roughly denormalize by 10x...probably don't want to do that yet.

# water_system_facilities - PWSID + facility_id is unique
# There are ~300 PWSID's in water_system but not water_system_facilities
sdwis_wsf = pd.read_csv(data_path + "/sdwis_water_system_facility.csv")

# Filter to only pws's that we're interested in
sdwis_wsf = sdwis_wsf.loc[sdwis_wsf["pwsid"].isin(sdwis["pwsid"])]

sdwis_wsf.head()


#%%
##############################################
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
    data_path + "/frs.geojson")

frs = frs.set_crs(EPSG, allow_override=True)

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

#%%

##############################################
# 3) TIGRIS
##############################################
tigris = gpd.read_file(data_path + "/tigris_places_clean.geojson")

tigris = tigris.set_crs(EPSG, allow_override=True)

# keep_columns = ["STATEFP", "GEOID", "NAME", "NAMELSAD"]
# tigris = tigris[keep_columns]

# Standardize data type
tigris["statefp"] = tigris["statefp"].astype("int")

# Augment with state abbrev
tigris = tigris.join(crosswalk, on="statefp", how="inner")

# GEOID seems to be a safe unique identifier
tigris.head()

#%%

##############################################
# 6?) How about echo?
##############################################

echo = pd.read_csv(
    data_path + "/echo.csv",
    usecols=["pwsid", "fac_lat", "fac_long", "fac_name"],
    dtype="string")

# Filter to only those in our SDWIS list and with lat/long
# 53,500 SDWIS match to ECHO, 2209 don't match
echo = echo.loc[
    echo["pwsid"].isin(sdwis["pwsid"]) &
    echo["fac_lat"].notna()].copy()

echo.head()

#%%

# Convert FRS to 4326
frs = frs.to_crs(epsg="4326")

# Convert echo to GeoPandas
echo = gpd.GeoDataFrame(
    echo,
    geometry=gpd.points_from_xy(echo["fac_long"], echo["fac_lat"]))

# Join on PWSID.
# 45,584 matches between FRS and Echo
# Problem: GeoPandas only allows one geometry column, and we need to take the distances.
# Solution: https://stackoverflow.com/questions/58276632/is-it-bad-practice-to-have-more-than-1-geometry-column-in-a-geodataframe
# Drop geometries. Join them. Make it a GeoDataFrame for one of the geometries. Ensure similar CRS.
# Write a function to calculate distance for the other geometry. Apply.
join = echo.merge(frs, on="pwsid", how="inner")

#%%

##########################################
# What next?
##########################################

"""
I want to create a stacked merge report.

1) Map to a unified data model:
    - source system name
    - source system key
    - pwsid
    - name
    - city served?
    - lat?
    - long?
    - geometry? - Either multiple columns for different geometry quality, or smart survivorship
        - shape
        - point
        - zip centroid
        - geometry_quality - (Opt?) Notes about the quality; e.g. whether it came from a zip, from multiple points that were averaged, etc

2)  pwsid will serve as the merge ID. We probably don't need a separate merge ID,
    unless it turns out that some pwsid's are wrong.

3) Matching:
    - SDWIS is the anchor.
    - FRS / ECHO match easily on PWSID. Easy to assign MK. 
        - Or I could just join directly to SDWIS. pwsid is unique in ECHO, not in FRS
    - TIGRIS will need spatial matching, fuzzy name matching, and manual review.
    - MHP will need spatial matching, fuzzy name matching, and manual review.
    - Boundaries:
        - OK has good PWSID matching. But are the boundaries right? They look pretty weird.

"""


#%%

# OK! Let's do that then.