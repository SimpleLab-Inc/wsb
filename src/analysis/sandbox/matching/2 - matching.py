#%%

import os
from typing import List, Optional
import pandas as pd
import geopandas as gpd
from dotenv import load_dotenv
import sqlalchemy as sa

load_dotenv()

pd.options.display.max_columns = None

DATA_PATH = os.environ["WSB_STAGING_PATH"]
OUTPUT_PATH = os.path.join(DATA_PATH, "..", "outputs")
EPSG = os.environ["WSB_EPSG"]

# Connect to local PostGIS instance
conn = sa.create_engine(os.environ["POSTGIS_CONN_STR"])


#%%
# Load up the supermodel

# Alternative - load from file
#supermodel = gpd.read_file(OUTPUT_PATH + "/supermodel.csv")

supermodel = gpd.GeoDataFrame.from_postgis(
    "SELECT * FROM utility_xref;", conn, geom_col="geometry")


#%% ##############################
# More Cleansing (or this could move to script #1, or into the tokenization)
##################################

# These words often (but not always) indicate a mobile home park
regex = r"\b(?:MOBILE|TRAILER|MHP|TP|CAMPGROUND|RV)\b"

supermodel["likely_mhp"] = (
    (supermodel["source_system"] == "mhp") |
    (
        supermodel["source_system"].isin(["echo", "sdwis"]) &
        supermodel["name"].notna() &
        supermodel["name"].fillna("").str.contains(regex, regex=True)
    ))

# These words often (but not always) indicate a mobile home park
regex = r"\b(?:VILLAGE|MANOR|ACRES|ESTATES)\b"

supermodel["possible_mhp"] = (
    (supermodel["source_system"] == "mhp") |
    (supermodel["likely_mhp"] == "mhp") |
    (
        supermodel["source_system"].isin(["echo", "sdwis"]) &
        supermodel["name"].notna() &
        supermodel["name"].fillna("").str.contains(regex, regex=True)
    ))


#%%

# Just a little standardization on this column
supermodel["geometry_quality"] = (supermodel["geometry_quality"]
    .str.upper()
    .replace({
        "ZIP CODE-CENTROID": "ZIP CODE CENTROID"
    }))

#%% ##########################
# Now on to the matching.
##############################

"""
Matching

1)  pwsid will serve as the merge ID. We probably don't need a separate merge ID,
    unless it turns out that some pwsid's are wrong.

2) Matching:
    - SDWIS is the anchor.
    - FRS / ECHO match easily on PWSID. Easy to assign MK. 
        - Or I could just join directly to SDWIS. pwsid is unique in ECHO, not in FRS
    - TIGER will need spatial matching, fuzzy name matching, and manual review.
    - MHP will need spatial matching, fuzzy name matching, and manual review.
    - Boundaries:
        - OK has good PWSID matching. But are the boundaries right? They look pretty weird.

# Match rules:
# 1) ECHO point inside TIGER geometry
# 2) Matching state AND tokenized facility name
# 3) Matching state and tokenized city served
# 4) Combos of the above
"""


# We'll use this for name matching
def tokenize_ws_name(series) -> pd.Series:
    replace = (
        r"(CITY|TOWN|VILLAGE)( OF)?|WSD|HOA|WATERING POINT|LLC|PWD|PWS|SUBDIVISION" +
        r"|MUNICIPAL UTILITIES|WATERWORKS|MUTUAL|WSC|PSD|MUD" +
        r"|(PUBLIC |RURAL )?WATER( DISTRICT| COMPANY| SYSTEM| WORKS| DEPARTMENT| DEPT| UTILITY)?"
    )

    return (series
        .str.upper() # Standardize to upper-case
        .str.replace(fr"\b({replace})\b", "", regex=True) # Remove water and utility words
        .str.replace(r"[^\w ]", " ", regex=True) # Replace non-word characters
        .str.replace(r"\s\s+", " ", regex=True) # Normalize spaces
        .str.strip())

def tokenize_mhp_name(series) -> pd.Series:
    
    # NOTE: It might be better to do standardizations instead of replacing with empty
    replace = (
        r"MOBILE (HOME|TRAILER)( PARK| PK)?|MOBILE (ESTATE(S?)|VILLAGE|MANOR|COURT|VILLA|HAVEN|RANCH|LODGE|RESORT)|" + 
        r"MOBILE(HOME|LODGE)|MOBILE( PARK| PK| COM(MUNITY)?)|MHP"
    )

    return (series
        .str.upper() # Standardize to upper-case
        .str.replace(fr"\b({replace})\b", "", regex=True) # Remove MHP words
        .str.replace(r"[^\w ]", " ", regex=True) # Replace non-word characters
        .str.replace(r"\s\s+", " ", regex=True) # Normalize spaces
        .str.strip())


def run_match(match_rule:str, left_on: List[str], right_on: Optional[List[str]] = None, left_mask = None, right_mask = None):
    
    if right_on is None:
        right_on = left_on

    left = tokens if left_mask is None else tokens.loc[left_mask]
    right = tokens if right_mask is None else tokens.loc[right_mask]

    matches = (left
        .merge(
            right,
            left_on=left_on,
            right_on=right_on)
        [["xref_id_x", "xref_id_y"]])

    matches["match_rule"] = match_rule

    return matches

#%%

# Create a token table and apply standardizations
tokens = supermodel[[
    "source_system", "xref_id", "master_key", "state", "name", "city_served",
    "address_line_1", "city",
    "geometry", "geometry_quality", "likely_mhp", "possible_mhp"
    ]].copy()

tokens["name_tkn"] = tokenize_ws_name(tokens["name"])
tokens["mhp_name_tkn"] = tokenize_mhp_name(tokens["name"])


# In general, we'll be matching sdwis/echo to tiger
# SDWIS, ECHO, and FRS are already matched - they'll go on the left.
# TIGER needs to be matched - it's on the right.
# UCMR is already matched, and doesn't add any helpful matching criteria, so we exclude it. Exception: IF it's high quality, it might be helpful in spatial matching to TIGER?

#%%

# Output as a sorted table to visually inspect
(tokens
    .sort_values(["state", "name_tkn"])
    .drop(columns=["geometry"])
    .to_csv(OUTPUT_PATH + "/match_sort.csv"))


#%%
# Rule: Match on state + name
# 25,073 matches

new_matches = run_match(
    "state+name",
    ["state", "name_tkn"],
    left_mask = (
        tokens["source_system"].isin(["sdwis", "echo", "frs"]) &
        tokens["state"].notna() &
        tokens["name_tkn"].notna()),
    right_mask = (
        tokens["source_system"].isin(["tiger", "mhp"]) &
        tokens["state"].notna() &
        tokens["name_tkn"].notna()))

print(f"State+Name matches: {len(new_matches)}")

matches = new_matches

#%%
# Rule: Spatial matches
# 12,109 matches between echo/frs and tiger
# (Down from 22,200 before excluding state, county, and zip centroids)

left_mask = (
    tokens["source_system"].isin(["echo", "frs"]) &
    (~tokens["geometry_quality"].isin(["STATE CENTROID", "COUNTY CENTROID", "ZIP CODE CENTROID"])))

right_mask = tokens["source_system"].isin(["tiger"])

new_matches = (tokens[left_mask]
    .sjoin(tokens[right_mask], lsuffix="x", rsuffix="y")
    [["xref_id_x", "xref_id_y"]]
    .assign(match_rule="spatial"))

print(f"Spatial matches: {len(new_matches)}")

matches = pd.concat([matches, new_matches])

#%%
# Rule: match state+city_served to state&name
# 16,302 matches

new_matches = run_match(
    "state+city_served",
    left_on = ["state", "city_served"],
    right_on = ["state", "name_tkn"],
    left_mask = (
        tokens["source_system"].isin(["sdwis"]) &
        tokens["state"].notna() &
        tokens["city_served"].notna()),
    right_mask = (
        tokens["source_system"].isin(["tiger"]) &
        tokens["state"].notna() &
        tokens["name_tkn"].notna()))

print(f"Match on city_served: {len(new_matches)}")

matches = pd.concat([matches, new_matches])

#%%
# Rule: match MHP's by tokenized name
# 1186 matches. Not great, but then again, not all MHP's will have water systems.
# Match on city too?

# Unfortunately, half of the "MHP" system has no names
# But they do have addresses that we could potentially match on

new_matches = run_match(
    "state+mhp_name",
    ["state", "mhp_name_tkn"],
    left_mask = (
        tokens["source_system"].isin(["sdwis", "echo", "frs"]) &
        tokens["possible_mhp"] &
        tokens["state"].notna() &
        tokens["mhp_name_tkn"].notna()),
    right_mask = (
        tokens["source_system"].isin(["mhp"]) &
        tokens["state"].notna() &
        tokens["mhp_name_tkn"].notna()))

print(f"Match on mhp: {len(new_matches)}")

matches = pd.concat([matches, new_matches])

#%%
# Rule: match MHP's by state + city + address
# 1186 matches. Not great, but then again, not all MHP's will have water systems.
# Match on city too?

# Unfortunately, half of the "MHP" system has no names
# But they do have addresses that we could potentially match on

new_matches = run_match(
    "mhp state+address",
    ["state", "city", "address_line_1"],
    left_mask = (
        tokens["source_system"].isin(["sdwis", "echo", "frs"]) &
        tokens["possible_mhp"] &
        tokens["state"].notna() &
        tokens["mhp_name_tkn"].notna()),
    right_mask = (
        tokens["source_system"].isin(["mhp"]) &
        tokens["state"].notna() &
        tokens["mhp_name_tkn"].notna()))

print(f"Match on mhp address: {len(new_matches)}")

matches = pd.concat([matches, new_matches])

# #%%
# # Export the likely MHP's sorted by state and name so we can see the kind of cleansing necessary
# # MHP name match
# # Sorting by state + name
# (tokens.loc[
#         tokens["possible_mhp"] &
#         tokens["name"].notna()]   
#     .drop(columns=["geometry", "city_served"])
#     .sort_values(["state", "city", "name_tkn"])
#     .to_excel(OUTPUT_PATH + "/mhp_stack.xlsx", index=False))

# #%%
# # Sorting by state + address
# tokens[tokens["likely_mhp"]].sort_values(["state", "city", "address_line_1"])

#%%

# Save the matches
matches.to_csv(OUTPUT_PATH + "/matches.csv")

#%% ################################
# Convert matches to MK matches.
####################################

mk_xwalk = supermodel[["xref_id", "master_key"]].set_index("xref_id")

mk_matches = (matches
    .join(mk_xwalk, on="xref_id_x").rename(columns={"master_key": "master_key_x"})
    .join(mk_xwalk, on="xref_id_y").rename(columns={"master_key": "master_key_y"})
    [["master_key_x", "master_key_y", "match_rule"]])

# Deduplicate
mk_matches = (mk_matches
    .groupby(["master_key_x", "master_key_y"])["match_rule"]
    .apply(lambda x: list(pd.Series.unique(x)))
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

# Convert Python lists to strings
stacked_match["match_rule"] = stacked_match["match_rule"].astype(str)

#%%
# Output the report
(stacked_match
    .drop(columns=["geometry"])
    .to_excel(OUTPUT_PATH + "/stacked_match_report.xlsx", index=False))

#%%
stacked_match.to_csv(OUTPUT_PATH + "/stacked_match_report.csv", index=False)

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

# Stats?
mk_matches["match_rule"].value_counts()
#%%

"""
Match types:
[state+city_served]                         7931
[state+name]                                5159
[spatial]                                   4258
[state+name, spatial, state+city_served]    3294
[state+name, state+city_served]             3108
[state+name, spatial]                       2191
[spatial, state+city_served]                1969
[state+name, state+mhp_name]                 358
[state+mhp_name]                             357

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

# Visualize in Leaflet
subset[
    ~subset["geometry"].is_empty &
    subset["geometry"].notna()
    ].explore(tooltip=False, popup=True)

#%%

"""

TODO:
- [ ] Pull in more data
    - [X] MHP
    - [X] UCMR
    - [ ] wsb_labeled.geojson

- [x] Trim "MHP", "Mobile Home Park" from name on MHP matching

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

#%%
"""

Let's study the types of matches. 
- Spatial:
    I suspect we'll want to filter out county and zip centroid matches on the spatial.
    There are lots of bad spatial matches for small utilities within the major region. How to fix these?
        Require name matches too?
        Look for TIGER's that match many and try to pick the best match?
- State+name match - require county
- Analyze points that are stacked atop each other
"""