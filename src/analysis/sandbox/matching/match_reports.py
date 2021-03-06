#%%

import os
import pandas as pd
import geopandas as gpd
from dotenv import load_dotenv
import sqlalchemy as sa

load_dotenv()

pd.options.display.max_columns = None

OUTPUT_PATH = os.environ["WSB_OUTPUT_PATH"]
EPSG = os.environ["WSB_EPSG"]

# Connect to local PostGIS instance
conn = sa.create_engine(os.environ["POSTGIS_CONN_STR"])


#%%
# Load up the supermodel

supermodel = gpd.GeoDataFrame.from_postgis(
    "SELECT * FROM pws_contributors;", conn, geom_col="geometry")

mk_matches = pd.read_sql("SELECT * FROM matches;", conn)

#%%

# This is helpful in a few places
masters = supermodel[supermodel["source_system"] == "sdwis"]["master_key"]

#%% ################################
# Report some stats
####################################

distinct_pwsid_matches = mk_matches['master_key'].drop_duplicates()
total_pwsid_count = len(masters)
labeled_pwsids = supermodel[supermodel["source_system"] == "labeled"]["pwsid"]

print(
    f"Distinct PWSID's with candidate matches: {len(distinct_pwsid_matches):,}" +
    f" ({(len(distinct_pwsid_matches) / total_pwsid_count)*100:.1f}%)")

# 32,013 distinct pwsid's have matches to TIGER or MHP. Interesting! 64.7%.

# Distinct PWSID's with labeled matches
print(
    f"Distinct PWSID's with labeled data: {len(labeled_pwsids):,}" +
    f" ({(len(labeled_pwsids) / total_pwsid_count)*100:.1f}%)")

# Total coverage across known labels and match candidates
total_coverage_count = len(pd.concat([distinct_pwsid_matches, labeled_pwsids]).drop_duplicates())
print(
    f"Total coverage:  {total_coverage_count:,}" +
    f" ({(total_coverage_count / total_pwsid_count)*100:.1f}%)")

#%%

# Stats on match rules
"""
Match types:
{spatial}                                          7069
{state+city_served}                                7038
{state+name}                                       4740
{state+name,spatial,state+city_served}             3717
{spatial,state+city_served}                        2862
{state+name,state+city_served}                     2685
{state+name,spatial}                               2608
{state+name,state+mhp_name}                         337
{state+mhp_name}                                    332
{"mhp state+address"}                                37
{state+name,state+mhp_name,"mhp state+address"}      21
{state+mhp_name,"mhp state+address"}                 17
{state+name,"mhp state+address"}                      2

Rules taking shape:
- If we have a state+name or state+city_served match, and a different spatial match, trash the spatial match.
    - Possible variation: Only do this if it's a zip or county centroid. Counterexample: There are some bad address matches.
"""

mk_matches["match_rule"].value_counts()


#%% ###########################
# Generate a stacked match report (for manual review)
###############################

# This will include all contributors where the master key is already known and there is a match to TIGER
anchors = supermodel[supermodel["master_key"].isin(mk_matches["master_key"])]

candidates = (supermodel
    .drop(columns="master_key")
    .merge(mk_matches, left_on="contributor_id", right_on="candidate_contributor_id")
    .rename(columns={"master_key": "mk_match"}))

#%%

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

#%% ###########################
# Save the report
###############################

(stacked_match
    .drop(columns=["geometry"])
    .to_excel(OUTPUT_PATH + "/stacked_match_report.xlsx", index=False))

#%% ###########################
# This geojson file supports the R Shiny app
###############################

stacked_match.to_file(OUTPUT_PATH + "/stacked_match_report.geojson", index=False)

#%% ###########################
# The "unmatched" report helps ID why records didn't match
###############################

tokens = pd.read_sql("SELECT * FROM tokens;", conn)

# Unmatched report
anchors = tokens[
    tokens["source_system"].isin(["sdwis"]) & 
    (~tokens["master_key"].isin(mk_matches["master_key"]))]

candidates = tokens[
    (tokens["source_system"] == "tiger")
    # Let's include ALL tiger, not just unmatched
    #& (~tokens["master_key"].isin(mk_matches["master_key_y"]))
    ]

umatched_report = pd.concat([anchors, candidates]).sort_values(["state", "name_tkn"])

#%%
umatched_report.to_excel("unmatched_report.xlsx", index=False)


#%% #########################################
# Some more stats
#############################################

# How many distinct records did each master match to?

matches_with_system = (mk_matches
    .merge(
        supermodel[["contributor_id", "source_system"]],
        left_on="candidate_contributor_id", right_on="contributor_id"))

# For each MK that matched, get counts of how many of each system it matched to
match_counts = (matches_with_system
    .groupby(["master_key", "source_system"])
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
    .groupby(["candidate_contributor_id", "source_system"])
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
