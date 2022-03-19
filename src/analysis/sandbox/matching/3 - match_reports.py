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

supermodel = gpd.GeoDataFrame.from_postgis(
    "SELECT * FROM utility_xref;", conn, geom_col="geometry")

matches = pd.read_sql("SELECT * FROM matches;", conn)

# This is helpful in a few places
masters = supermodel[supermodel["source_system"] == "sdwis"]["master_key"]

#%% ################################
# Convert matches to MK matches.
####################################

# The left side contains known PWS's and can be deduplicated by crosswalking to the master_key (pwsid)
# The right side contains unknown (candidate) matches and could stay as an xref_id

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

distinct_pwsid_matches = len(mk_matches['master_key_x'].unique())
total_pwsids = len(masters)

print(f"Distinct master matches: {len(mk_matches)}")
print(
    f"Distinct PWSID matches: {distinct_pwsid_matches}" +
    f" ({(distinct_pwsid_matches / total_pwsids)*100:.1f}%)")

# 32,013 distinct pwsid's have matches to TIGER or MHP. Interesting! 64.7%.

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
stacked_match.to_file(OUTPUT_PATH + "/stacked_match_report.geojson", index=False)

#%%

tokens = pd.read_sql("SELECT * FROM tokens;", conn)

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

#%% ###################################
# Match Stats
#######################################

# Stats on match rules
"""
Match types:
[spatial]                                          12042
[state+city_served]                                 6707
[state+name]                                        4698
[state+name, spatial, state+city_served]            3728
[spatial, state+city_served]                        3193
[state+name, state+city_served]                     2674
[state+name, spatial]                               2650
[state+mhp_name]                                     339
[state+name, state+mhp_name]                         337
[mhp state+address]                                   37
[state+name, state+mhp_name, mhp state+address]       21
[state+mhp_name, mhp state+address]                   18
[state+name, mhp state+address]                        2

Rules taking shape:
- If we have a state+name or state+city_served match, and a different spatial match, trash the spatial match.
    - Possible variation: Only do this if it's a zip or county centroid. Counterexample: There are some bad address matches.
"""

mk_matches["match_rule"].value_counts()

#%%
# How many distinct records did each master match to?

# Join the masters to the candidate match keys + source_system
# 49,445 masters

#%%

matches_with_system = (mk_matches
    .merge(supermodel[["master_key", "source_system"]], left_on="master_key_y", right_on="master_key"))

# For each MK that matched, get counts of how many of each system it matched to
match_counts = (matches_with_system
    .groupby(["master_key_x", "source_system"])
    .size()
    .unstack())

# Join match counts to the full set of masters (to include those that matched to nothing)
mk_match_counts = (masters
    .to_frame()
    .join(match_counts, on="master_key", how="left")
    .fillna(0))

print("PWS matches to distinct TIGER's and MHP's:")
mk_match_counts.agg(["mean", "median", "min", "max"])

#%%
# Plot it
mk_match_counts.hist()

#%%

# How about the other way around?
# Of the candidates that matched, how many masters did they match to?
mhp_and_tiger_matches = (matches_with_system
    .groupby(["master_key_y", "source_system"])
    .size())

(mhp_and_tiger_matches
    .groupby("source_system")
    .agg(["mean", "median", "min", "max"]))

#%%
# Histogram of MHP match counts
mhp_and_tiger_matches.loc[:,"mhp"].hist()

#%%
# LOG histogram of tiger match counts
mhp_and_tiger_matches.loc[:,"tiger"].hist(log=True, bins=20)

# Summary:
# Of the MHP's that matched, most matched to exactly 1, but some matched 2 or 3.
# Of the TIGER's that matched, most matched to 1, but a few outliers skew the mean up to 2

# So we might benefit by trying to refine the tigers. Or maybe it's OK that multiple PWS's match to them.


#%% #########################################
# Visualize specific match groups on a map
#############################################

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

Refinements:
- [ ] Try to get county on all data sources
- [ ] Assign a "type" to each water system, e.g. "Mobile Home Park", "Municipal", etc. This would tell us which match system will be stronger.
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

- [x] Consider: Create a Dash app for visualizing and stewarding potential matches (incl. leaflet map)?

# TODO: Add states to UCMR
# TODO: Have a geojson file of zip code geometries and centroids. Join to that later (if needed) instead of joining in the UCMR transformer.
# TODO: What type of centroid was most frequent in each of the match types?


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