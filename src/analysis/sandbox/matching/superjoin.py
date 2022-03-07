#%%

import os
from typing import Dict
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

#%% ##########################
# SDWIS/ECHO <-> TIGER - Spatial + Name matching
##############################

# Match rules:
# 1) ECHO point inside TIGER geometry
# 2) Matching state AND tokenized facility name
# 3) Matching state and tokenized city served
# 4) Combos of the above


# We'll use this for name matching
def tokenize_name(series) -> pd.Series:
    replace = (
        "(CITY|TOWN|VILLAGE)( OF)?|WSD|HOA|WATERING POINT|LLC|PWD|PWS|SUBDIVISION" +
        "|MUNICIPAL UTILITIES|WATERWORKS|MUTUAL|WSC|PSD|MUD" +
        "|(PUBLIC |RURAL )?WATER( DISTRICT| COMPANY| SYSTEM| WORKS| DEPARTMENT| DEPT| UTILITY)?"
    )

    return (series
        .str.upper() # Standardize to upper-case
        .str.replace(fr"\b({replace})\b", "", regex=True) # Remove water and utility words
        .str.replace(r"[^\w ]", " ", regex=True) # Replace non-word characters
        .str.replace(r"\s\s+", " ", regex=True) # Normalize spaces
        .str.strip())

#%%
# Woot! We have spatial matches. 23k
join = tiger.sjoin(echo, how="inner")

print(f"Spatial matches: {len(join)}")

# Supplement with sdwis pws_name and city_served
join = join.merge(sdwis[["pwsid", "pws_name", "city_served"]], on="pwsid")

join.head()


#%%

# How many distinct geoids had matches? 10,446
print("Distinct geoids: " + str(len(join["geoid"].unique())))
# How many matches per geoid? 2.2 avg, 1 min, 617 max (whoa! It's Houston)
print("Mean: " + str(join.groupby("geoid").size().mean()))
print("Min: " + str(join.groupby("geoid").size().min()))
print("Max: " + str(join.groupby("geoid").size().max()))


#%%
# Tokenize names (strip out common words and acronyms)
join["tiger_name"] = tokenize_name(join["name"])
join["echo_name"] = tokenize_name(join["fac_name"])
join["sdwis_pws_name"] = tokenize_name(join["pws_name"])

join.head()

# Narrowed to 4643 when you match tokenized echo_name == tiger_name
matches = join[join["tiger_name"] == join["echo_name"]][["geoid", "pwsid"]].assign(match_type = "spatial+name_token")

# 7232 matches on city_served == tiger_name. That's surprisingly good!
matches = pd.concat([
    matches,
    join[join["city_served"] == join["tiger_name"]][["geoid", "pwsid"]].assign(match_type = "spatial+city_served")])

# 6107 matches on tokenized sdwis_pws_name == tiger_name
matches = pd.concat([
    matches,
    join[join["sdwis_pws_name"] == join["tiger_name"]][["geoid", "pwsid"]].assign(match_type = "spatial+sdwis_pws_name")])

#%%

# Combine and dedupe matches, with: city_served > name_token > sdwis_pws_name. 9755 remaining
matches = matches.sort_values(["geoid", "pwsid", "match_type"]).drop_duplicates(subset=["geoid", "pwsid"], keep="first")

print(f"Distinct matches on spatial & (facility name or city served): {len(matches)}")

#%%
# Filter the spatial join based on the name matches we just found
join_sub = join.merge(matches, on=["geoid", "pwsid"], how="inner")

#%%
# How many distinct geoids had matches? 7676
len(join_sub["geoid"].unique())

#%%
# How many matches per geoid? 1.3 avg, 1 min, 83 max (Raleigh this time. City served might worsen matches!)
# This is getting closer to 1:1
print("Mean: " + str(join_sub.groupby("geoid").size().mean()))
print("Median: " + str(join_sub.groupby("geoid").size().median()))
print("Min: " + str(join_sub.groupby("geoid").size().min()))
print("Max: " + str(join_sub.groupby("geoid").size().max()))

# This seems like a decent stopping point.

#%% ##########################
# Generate the final table
##############################

"""
Requested table:

Column                   | Data Source
-------------------------|----------------
pwsid                    | SDWIS
pws_name                 | SDWIS
wsb                      | WSB (hold for now)
tiger_match              | TIGER - Rather than just a bool, let's include the geoid and how it matched
echo_match               | ECHO - Rather than just a bool, let's include the lat/long and method
mhp_match                | MHP - hold for now
state_code               | SDWIS
county_served            | SDWIS
city_served              | SDWIS
population_served        | SDWIS
connections              | SDWIS
primacy_agency_code      | SDWIS
service_area_type_code   | SDWIS
"""

output = sdwis[[
    "pwsid", "pws_name", "primacy_agency_code", "state_code", "city_served",
    "county_served", "population_served_count", "service_connections_count",
    "service_area_type_code", "owner_type_code"
]]

# Supplement with tiger match info
output = (output
    .merge(join_sub[["pwsid", "geoid", "match_type"]], on="pwsid", how="left")
    .rename(columns={
        "geoid": "tiger_match_geoid",
        "match_type": "tiger_match_type"
    }))

# Supplement with echo match info
output = (output
    .merge(echo[["pwsid", "fac_lat", "fac_long", "fac_collection_method",
                 "fac_street", "fac_city", "fac_state", "fac_zip", "fac_county", 
                 'fac_reference_point', 'fac_accuracy_meters', 
                 'fac_indian_cntry_flg', 'fac_percent_minority', 'fac_pop_den', 'ejscreen_flag_us']], on="pwsid", how="left")
    .rename(columns={
        "fac_lat": "echo_latitude",
        "fac_long": "echo_longitude",
        "fac_collection_method": "echo_geocode_method"
    }))

# Verify: We should still have exactly the number of pwsid's as we started with
if not (len(output) == len(sdwis)):
    raise Exception("Output was filtered or denormalized")

#%%
# This should probably go to some other folder
output.to_csv(DATA_PATH + "/matched_output.csv")