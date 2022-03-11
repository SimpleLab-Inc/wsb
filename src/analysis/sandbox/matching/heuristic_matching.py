#%%

import os
import pandas as pd
import geopandas as gpd
from dotenv import load_dotenv

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

echo.head()

#%% ##########################################
# FRS
##############################################

frs = gpd.read_file(
    DATA_PATH + "/frs.geojson")

# keep_columns = [
#     "PGM_SYS_ID", "LATITUDE83", "LONGITUDE83", "ACCURACY_VALUE", 
#     "COLLECT_MTH_DESC", "REF_POINT_DESC", "geometry"]
#
#frs = frs[keep_columns]

# Filter to those in SDWIS
# And only those with interest_type "WATER TREATMENT PLANT". Other interest types are already in Echo.
frs = frs[
    frs["pwsid"].isin(sdwis["pwsid"]) &
    (frs["interest_type"] == "WATER TREATMENT PLANT")]

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

print(f"{len(frs)} FRS entries remain after removing echo duplicates")


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
    address_line_1       = sdwis["address_line1"],
    address_line_2       = sdwis["address_line2"],
    city                 = sdwis["city_name"],
    zip                  = sdwis["zip_code"],
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
    xref_id                 = "frs." + frs["pwsid"], # This isn't actually unique, but makes it simpler to drop dupes
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
).drop_duplicates()

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

supermodel = pd.concat([
    sdwis_supermodel,
    echo_supermodel,
    frs_supermodel,
    ucmr_supermodel,
    tiger_supermodel
])

# Reset the CRS - it gets lost in the concat (maybe because sdwis has no CRS)
supermodel = supermodel.set_crs(epsg=EPSG, allow_override=True)

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
tokens = supermodel[["source_system", "xref_id", "master_key", "state", "name", "city_served", "geometry"]].copy()

tokens["name_tkn"] = tokenize_name(tokens["name"])
tokens["state"] = tokens["state"].str.upper()
tokens["city_served"] = tokens["city_served"].str.upper()

#%%

# Output as a sorted table to visually inspect
(tokens
    .sort_values(["state", "name_tkn"])
    .drop(columns=["geometry"])
    .to_csv("match_sort.csv"))

#%%

# In general, we'll be matching sdwis/echo to tiger
# SDWIS, ECHO, and FRS are already matched - they'll go on the left.
# TIGER needs to be matched - it's on the right.
# UCMR is already matched, and doesn't add any helpful matching criteria, so we exclude it. Exception: IF it's high quality, it might be helpful in spatial matching to TIGER?

mask = tokens["source_system"].isin(["sdwis", "echo", "frs"])
left = tokens[tokens["source_system"].isin(["sdwis", "echo", "frs"])]
right = tokens[tokens["source_system"].isin(["tiger"])]

#%%
# Rule: Match on state + name
# 23,542 matches
new_matches = (left
    .merge(right, on=["state", "name_tkn"], how="inner")
    [["xref_id_x", "xref_id_y"]]
    .assign(match_rule="state+name"))

print(f"State+Name matches: {len(new_matches)}")

matches = new_matches

#%%
# Rule: Spatial matches
# 21k matches between echo and tiger
new_matches = (left
    .sjoin(right, lsuffix="x", rsuffix="y")
    [["xref_id_x", "xref_id_y"]]
    .assign(match_rule="spatial"))

print(f"Spatial matches: {len(new_matches)}")

matches = pd.concat([matches, new_matches])


#%%
# Rule: match state+city_served to name

new_matches = (left
    .merge(right, left_on=["state", "city_served"], right_on=["state", "name_tkn"])
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

# This will include all XREFs where the master key is already known and there is a match to TIGER
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

# Let's add a "color" column that just toggles on and off per match group
# First, we'll number each match group. Then, we'll color odd numbers.
stacked_match["color"] = (stacked_match["mk_match"].rank(method="dense") % 2) == 0

#%%
# Output the report
(stacked_match
    .drop(columns=["geometry"])
    .to_excel(OUTPUT_PATH + "/stacked_match_report3.xlsx", index=False))

#%%

# Unmatched report
anchors = tokens[
    tokens["source_system"].isin(["sdwis"]) & 
    (~tokens["master_key"].isin(mk_matches["master_key_x"]))]

candidates = tokens[
    (tokens["source_system"] == "tiger")
    # Let's include ALL tiger, not just unmatched
    #& (~tokens["master_key"].isin(mk_matches["master_key_y"]))
    ]

umatched_report = pd.concat([anchors, candidates]).sort_values(["state", "name_tkn"])

umatched_report["geometry_type"] = umatched_report["geometry"].geom_type
umatched_report = umatched_report.drop(columns=["geometry"])

#%%
umatched_report.to_excel("unmatched_report.xlsx", index=False)

#%%

# Could I get a few sample little maps? for the report?
# Stats on matches in each direction?

#%%

# Stats?
mk_matches["match_rule"].value_counts()

"""
Match types:
[spatial]                                                      11795 - Weak? Likely lots of centroids, lots of overlap
[state+city_served<->name]                                      6721 - Strong matches. Could improve lat/long with these
[state+name, state+name]                                        3318
[spatial, state+city_served<->name]                             3186 - Very strong matches
[state+name, state+name, spatial, state+city_served<->name]     2938
[state+name, state+name, state+city_served<->name]              2349
[state+name, state+name, spatial]                               1569
[state+name, spatial]                                            937
[state+name]                                                     792
[state+name, spatial, state+city_served<->name]                  721
[state+name, state+city_served<->name]                           387

Rules taking shape:
- If we have a state+name or state+city_served match, and a different spatial match, trash the spatial match.
    - Possible variation: Only do this if it's a zip or county centroid. Counterexample: There are some bad address matches.
"""

#%%
# TODO: What type of centroid was most frequent in each of the match types?

#%%

# How many distinct records did each SDWIS match to?
# Pretty close to 1. That's good.
# But we'll need to analyze those 1:N's.
print("PWS matches to distinct TIGER's:")
print("Mean: " + str(mk_matches.groupby("master_key_x").size().mean()))
print("Median: " + str(mk_matches.groupby("master_key_x").size().median()))
print("Min: " + str(mk_matches.groupby("master_key_x").size().min()))
print("Max: " + str(mk_matches.groupby("master_key_x").size().max()))

mk_matches.groupby("master_key_x").size().hist()
#%%
mk_matches.groupby("master_key_x").size().hist(log=True)

#%%

# How bout TIGER to SDWIS?
# 2 on average. Interesting.
print("TIGER matches to distinct SDWIS's:")
print("Mean: " + str(mk_matches.groupby("master_key_y").size().mean()))
print("Median: " + str(mk_matches.groupby("master_key_y").size().median()))
print("Min: " + str(mk_matches.groupby("master_key_y").size().min()))
print("Max: " + str(mk_matches.groupby("master_key_y").size().max()))

# Log histogram
mk_matches.groupby("master_key_y").size().hist(log=True, bins=100)

# Superjoin todo's:
# TODO: Add UCMR4 zip codes + centroids
# TODO: Add MHP's
# TODO: Add "Has WSB" flag (need to pull in all the WSB's)
# TODO: Consider a county match (maybe in cases where there are multiple state+name matches?)


#%%
stacked_match.head()

#%%
# Visualize specific match groups on a map
# 055293501 - This one matched two two separate polygons, one spatially, one on name.
# The name match is better.
# The spatial match is because the address is an admin address (Chippewa Indians Office)

subset = stacked_match[
    (stacked_match["mk_match"] == "043740039") &
    (stacked_match["geometry"].notna())]

# Assign a rank so that bigger polygons (in general) appear under smaller polygons and points
# subset["rank"] = subset["geometry_type"].map({
#         "Point": 1
#         "Polygon": 2,
#         "MultiPolygon": 3,
#     })

subset["area"] = subset["geometry"].area

subset = subset.sort_values("area", ascending=False)
subset

#%%

subset.explore(tooltip=False, popup=True)

#%%

"""

TODO:
- [ ] Pull in more data
    - [ ] MHP
    - [ ] UCMR
    - [ ] wsb_labeled.geojson

- [ ] Try to quantify error compared to labeled boundaries
- [ ] Spend a little time in the rabbit hole, then try to gen a new match output

- [ ] Do we have a summary of data sources, studies, etc
- [x] Plot some points
- [ ] Rate the quality of matches
    - [ ] Which matches are best quality? Review
    - [ ] Why is there so little overlap between spatial and name matches? Research.
    - [ ] Assign match scores based on match type. Try to get population covered.
- [ ] Rate the quality of geocodes
    - [ ] Zip and county centroids are not great.
    - [ ] Centroids that overlap could be bad (e.g. admin offices)
    - Possibly: Don't do spatial match rule on county centroids

- [ ] Consider: Create a Dash app for visualizing and stewarding potential matches (incl. leaflet map)?



- Try adding a buffer around the polygons and rerun for matching
- If multiple spatial matches, use a min distance to "win"
- Do we want looser spatial matches? Even if we know it's not exact? N:1 Tiger:SDWIS is OK?
- Could we come up with some kind of "accuracy score" - involving spatial distance, # match rules, 

"""
