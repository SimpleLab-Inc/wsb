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
# Keep only "A" for active
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
# 47,951 SDWIS match to ECHO, 1494 don't match
echo_df = echo_df.loc[
    echo_df["pwsid"].isin(sdwis["pwsid"]) &
    echo_df["fac_lat"].notna()].copy()

# Convert to geopandas
echo: gpd.GeoDataFrame = gpd.GeoDataFrame(
    echo_df,
    geometry=gpd.points_from_xy(echo_df["fac_long"], echo_df["fac_lat"]),
    crs="EPSG:4326")

echo.head()


#%% ##########################################
# 7) UCMR
##############################################

# Primarily: This links pwsid to zip code.
# But something is making this a big file. Are there zip code polygons in here?
# Will we use that or do we just need the centroid?

# ucmr = gpd.read_file(DATA_PATH + "/ucmr.geojson")
# ucmr.head()

#%% #############################
# Mapping to a standard model
#################################

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
#Jess notes: retain a column for each geometry, and then a new column for the winning geom?
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
    - TIGER will need spatial matching, fuzzy name matching, and manual review.
    - MHP will need spatial matching, fuzzy name matching, and manual review.
    - Boundaries:
        - OK has good PWSID matching. But are the boundaries right? They look pretty weird.

"""


#%%
#jess note to ryan: do we want to retain the match_ids (e.g. tiger geoid, etc)?
model = {
    "source_system": "str",
    "source_system_id": "str",
    "master_key": "str",
    "name": "string",
    "fac_street": "string",
    "fac_city": "string",
    "fac_state": "string",
    "fac_zip": "string",
    "fac_county": "string",
    "city_served": "string",
    "primacy_agency_code": "string",
#    "geometry_shape": object,
    "geometry_lat": "string",
    "geometry_long": "string",
    "geometry": "object",
    "geometry_quality": "string"
}

supermodel = pd.DataFrame(columns=list(model.keys())).astype(model)

#%%

sdwis_supermodel = gpd.GeoDataFrame().assign(
    source_system_id     = sdwis["pwsid"],
    source_system        = "sdwis",
    xref_id              = "sdwis." + sdwis["pwsid"],
    master_key           = sdwis["pwsid"],
    pwsid                = sdwis["pwsid"],
    state                = sdwis["state_code"],
    name                 = sdwis["pws_name"],
    city_served          = sdwis["city_served"]
)

echo_supermodel = gpd.GeoDataFrame().assign(
    source_system_id        = echo["pwsid"],
    source_system           = "echo",
    xref_id                 = "echo." + echo["pwsid"],
    master_key              = echo["pwsid"],
    pwsid                   = echo["pwsid"],
    state                   = echo["fac_state"],
    name                    = echo["fac_name"],
    geometry_lat            = echo["fac_lat"],
    geometry_long           = echo["fac_long"],
    geometry                = echo["geometry"],
    geometry_quality        = echo["fac_collection_method"],
)

tiger_supermodel = gpd.GeoDataFrame().assign(
    source_system_id    = tiger["geoid"],
    source_system       = "tiger",
    xref_id             = "tiger." + tiger["geoid"],
    master_key          = pd.NA,
    name                = tiger["name"],
    state               = tiger["state"],
    geometry            = tiger["geometry"],
)

supermodel = pd.concat([
    sdwis_supermodel,
    echo_supermodel,
    tiger_supermodel
])

# Assign missing master keys as "UNK-"
mask = supermodel["master_key"].isna()
supermodel.loc[mask, "master_key"] = "UNK-" + pd.Series(range(mask.sum())).astype("str")

supermodel.sample(10)


#%% ##########################
# Now on to the matching.
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

# Create a token table and apply standardizations
tokens = supermodel[["source_system", "xref_id", "state", "name", "city_served", "geometry"]].copy()

tokens["name"] = tokenize_name(tokens["name"])
tokens["state"] = tokens["state"].str.upper()
tokens["city_served"] = tokens["city_served"].str.upper()

#%%

# Output as a sorted table to visually inspect
(tokens
    .sort_values(["state", "name"])
    .drop(columns=["geometry"])
    .to_csv("match_sort.csv"))

#%%

# In general, we'll be matching sdwis/echo to tiger
mask = tokens["source_system"].isin(["sdwis", "echo"])
left = tokens[mask]
right = tokens[~mask]

#%%
# Rule: Match on state + name
# 23,542 matches
new_matches = (left
    .merge(right, on=["state", "name"], how="inner")
    [["xref_id_x", "xref_id_y"]]
    .assign(match_rule="state+name"))

print(f"State+Name matches: {len(new_matches)}")

matches = new_matches

#%%
# Rule: Spatial matches
# 23k matches between echo and tiger
new_matches = (left
    .sjoin(right, lsuffix="x", rsuffix="y")
    [["xref_id_x", "xref_id_y"]]
    .assign(match_rule="spatial"))

print(f"Spatial matches: {len(new_matches)}")

matches = pd.concat([matches, new_matches])


#%%
# Rule: match state+city_served to name

new_matches = (left
    .merge(right, left_on=["state", "city_served"], right_on=["state", "name"])
    [["xref_id_x", "xref_id_y"]]
    .assign(match_rule="state+city_served<->name"))

print(f"Match on city_served: {len(new_matches)}")

matches = pd.concat([matches, new_matches])

#%%

# Convert matches to MK matches.

mk_xwalk = supermodel[["xref_id", "master_key"]].set_index("xref_id")

mk_matches = (matches
    .join(mk_xwalk, on="xref_id_x").rename(columns={"master_key": "master_key_x"})
    .join(mk_xwalk, on="xref_id_y").rename(columns={"master_key": "master_key_y"})
    [["master_key_x", "master_key_y", "match_rule"]])

# Deduplicate
mk_matches = (mk_matches
    .groupby(["master_key_x", "master_key_y"])["match_rule"]
    .apply(list)
    .reset_index())

print(f"Distinct master matches: {len(mk_matches)}")
print(f"Distinct PWSID matches: {len(mk_matches['master_key_x'].unique())}")

# 31k distinct pwsid matches. Interesting! 62%.

#%%
# Now, finally, the stacked match report.

anchors = supermodel[supermodel["master_key"].isin(mk_matches["master_key_x"])]

candidates = (supermodel
    .merge(mk_matches, left_on="master_key", right_on="master_key_y")
    .drop(columns="master_key_y")
    .rename(columns={"master_key_x": "mk_match"}))

base_columns = ["type", "mk_match", "match_rule"]
remainder = [c for c in candidates.columns if c not in base_columns]

stacked_match = (pd.concat([
        anchors.assign(type="anchor", mk_match=anchors["master_key"]),
        candidates.assign(type="candidate")])
    .sort_values(["mk_match", "type"])
    [base_columns + remainder]
    )

# Instead of actual geometry, which isn't very helpful in an Excel report, let's just sub in the type of geometry
# (We might want to leave the actual geometry if this will be consumed by R or something to create another report)
stacked_match["geometry_type"] = stacked_match["geometry"].geom_type
stacked_match = stacked_match.drop(columns=["geometry"])

#%%
stacked_match.to_excel("stacked_match_report.xlsx", index=False)


#%%
# Heuristic matching TODO's

# Superjoin todo's:
# TODO: Add UCMR4 zip codes + centroids
# TODO: Add MHP's
# TODO: Add "Has WSB" flag (need to pull in all the WSB's)
