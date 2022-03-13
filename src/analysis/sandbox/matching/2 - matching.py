#%%

import os
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

#%%

# Output as a sorted table to visually inspect
(tokens
    .sort_values(["state", "name_tkn"])
    .drop(columns=["geometry"])
    .to_csv(OUTPUT_PATH + "/match_sort.csv"))

#%%

# In general, we'll be matching sdwis/echo to tiger
# SDWIS, ECHO, and FRS are already matched - they'll go on the left.
# TIGER needs to be matched - it's on the right.
# UCMR is already matched, and doesn't add any helpful matching criteria, so we exclude it. Exception: IF it's high quality, it might be helpful in spatial matching to TIGER?

mask = tokens["source_system"].isin(["sdwis", "echo", "frs"])
left = tokens[tokens["source_system"].isin(["sdwis", "echo", "frs"])]
right = tokens[tokens["source_system"].isin(["tiger", "mhp"])]

#%%
# Rule: Match on state + name
# 25,073 matches

left_mask = left["state"].notna() & left["name_tkn"].notna()
right_mask = right["state"].notna() & right["name_tkn"].notna()

new_matches = (left[left_mask]
    .merge(right[right_mask], on=["state", "name_tkn"], how="inner")
    [["xref_id_x", "xref_id_y"]]
    .assign(match_rule="state+name"))

print(f"State+Name matches: {len(new_matches)}")

matches = new_matches

#%%
# Rule: Spatial matches
# 22,200 matches between echo and tiger
new_matches = (left
    .sjoin(right, lsuffix="x", rsuffix="y")
    [["xref_id_x", "xref_id_y"]]
    .assign(match_rule="spatial"))

print(f"Spatial matches: {len(new_matches)}")

matches = pd.concat([matches, new_matches])


#%%
# Rule: match state+city_served to state&name

left_mask = left["state"].notna() & left["city_served"].notna()
right_mask = right["state"].notna() & right["name_tkn"].notna()

new_matches = (left[left_mask]
    .merge(right[right_mask], left_on=["state", "city_served"], right_on=["state", "name_tkn"])
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
    .to_excel(OUTPUT_PATH + "/stacked_match_report.xlsx", index=False))

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
    - [X] MHP
    - [X] UCMR
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
