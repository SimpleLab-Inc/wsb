#%%

import os
import numpy as np
import pandas as pd
import geopandas as gpd
import sqlalchemy as sa
from dotenv import load_dotenv

load_dotenv()

STAGING_PATH = os.environ["WSB_STAGING_PATH"]
EPSG = os.environ["WSB_EPSG"]
PROJ = os.environ["WSB_EPSG_AW"]

# Connect to local PostGIS instance
conn = sa.create_engine(os.environ["POSTGIS_CONN_STR"])


#%%
# Load up the TIGER and LABELED data

print("Pulling in data from database...", end="")

supermodel = gpd.GeoDataFrame.from_postgis("""
        SELECT *
        FROM pws_contributors
        WHERE source_system IN ('labeled', 'tiger');""",
    conn, geom_col="geometry")

print("done.")

labeled = supermodel[supermodel["source_system"] == "labeled"]
tiger = supermodel[supermodel["source_system"] == "tiger"].set_index("contributor_id")

#%%
matches = pd.read_sql("""
    SELECT
        m.master_key,
        m.candidate_contributor_id,
        m.match_rule,
        c.source_system_id
    FROM matches m
    JOIN pws_contributors c ON m.candidate_contributor_id = c.contributor_id
    WHERE c.source_system = 'tiger';
    """, conn)

print("Read matches from database.")

#%% ##########################
# Generate some TIGER match stats
##############################

# How often do we match to multiple tigers?
pws_to_tiger_match_counts = (matches
    .groupby("master_key")
    .size())

pws_to_tiger_match_counts.name = "pws_to_tiger_match_count"

# Let's also do it the other direction
tiger_to_pws_match_counts = (matches
    .groupby("candidate_contributor_id")
    .size())

tiger_to_pws_match_counts.name = "tiger_to_pws_match_count"

# Augment matches with these TIGER match stats
# We don't use these downstream; they're just useful for debugging
# matches = (matches
#     .join(pws_to_tiger_match_counts, on="master_key")
#     .join(tiger_to_pws_match_counts, on="candidate_contributor_id"))

# 1850 situations with > 1 match
print(f"{(pws_to_tiger_match_counts > 1).sum()} PWS's matched to multiple TIGERs")

# 3631 TIGERs matched to multiple PWSs
print(f"{(tiger_to_pws_match_counts > 1).sum()} TIGER's matched to multiple PWS's")

#%% #########################
# Figure out our strongest match rules
#############################

"""
We'll compare the matches to the labeled data to determine which match
rules (and combos of rules) are most effective. Rank our matches based
on that, and select the top one.
"""

# Get a series with the labeled geometry for each PWS
s1 = gpd.GeoSeries(
    labeled[["pwsid", "geometry"]]
    .loc[labeled["master_key"].isin(matches["master_key"])]
    .set_index("pwsid")
    ["geometry"])

# TIGER candidates (note that this index will not be unique)
candidate_matches = gpd.GeoDataFrame(matches
    .join(tiger["geometry"], on="candidate_contributor_id")
    .rename(columns={"master_key": "pwsid"})
    .set_index("pwsid")
    [["geometry", "match_rule"]])

# Filter to only the PWS's that appear in both series
# 7,423 match
s1 = s1.loc[s1.index.isin(candidate_matches.index)]
candidate_matches = candidate_matches.loc[candidate_matches.index.isin(s1.index)]

# Switch to a projected CRS
s1 = s1.to_crs(PROJ)
candidate_matches = candidate_matches.to_crs(PROJ)

# This gives a warning, but it's OK
# "Indexes are different" - this is because tiger_matches has duplicated indices (multiple matches to the same PWS)
distances = s1.distance(candidate_matches, align=True)

# Not sure what causes NA. Filter only non-NA
distances = distances[distances.notna()]
distances.name = "distance"

# re-join to the match table
candidate_matches = candidate_matches.join(distances, on="pwsid", how="inner")

# Assign a score
PROXIMITY_BUFFER = 1000 # Meters
candidate_matches["score"] = candidate_matches["distance"] < PROXIMITY_BUFFER

#%%

# Assign a "rank" to each match rule and combo of match rules
match_ranks = (candidate_matches
    .groupby(["match_rule"])
    .agg(
        points = ("score", "sum"),
        total = ("score", "size")
    )) #type:ignore

match_ranks["score"] = match_ranks["points"] / match_ranks["total"]
match_ranks = match_ranks.sort_values("score", ascending=False)
match_ranks["rank"] = np.arange(len(match_ranks))

print("Identified best match rules based on labeled data.")

#%% ###########################
# Pick the best TIGER match
###############################

# Assign the rank back to the matches
matches_ranked = matches.join(match_ranks[["rank"]], on="match_rule", how="left")

# Sort by rank, then take the first one
best_match = (matches_ranked
    .sort_values(["master_key", "rank"])
    .drop_duplicates(subset=["master_key"], keep="first")
    [["master_key", "candidate_contributor_id"]])

print(f"Picked the 'best' TIGER matches: {len(best_match)} rows.")

#%%
best_match.to_sql("best_match", conn, if_exists="replace")
