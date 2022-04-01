# Let's use the labeled data to check some hypotheses.

#%%

import os
import pandas as pd
import geopandas as gpd
import sqlalchemy as sa
from dotenv import load_dotenv

load_dotenv()

DATA_PATH = os.environ["WSB_STAGING_PATH"] + "/../outputs"
EPSG = os.environ["WSB_EPSG"]

# Connect to local PostGIS instance
conn = sa.create_engine(os.environ["POSTGIS_CONN_STR"])

PROJ = os.environ["WSB_EPSG_AW"]

#%%
# Load up the data sources

supermodel = gpd.GeoDataFrame.from_postgis(
    "SELECT * FROM pws_contributors WHERE source_system NOT IN ('ucmr');",
    conn, geom_col="geometry")

candidates = supermodel[supermodel["source_system"].isin(["tiger", "mhp"])].set_index("contributor_id")
labeled = supermodel[supermodel["source_system"] == "labeled"]

matches = pd.read_sql("SELECT * FROM matches;", conn)


candidates = candidates.to_crs(PROJ)
labeled = labeled.to_crs(PROJ)


# Q: Which match type leads to the best results?
# Q: Are MHP matches good?
# Q: Are MHP points better than ECHO points?
# Q: What geometry_quality's result in good vs bad spatial matches? Perhaps there are some we could exclude.

#%%

# Q: Which match type leads to the best results?

# I need to get the labeled polygon in one series and the TIGER polygons + match types in another series
# Then join them on PWSID and find the distance between polygons
# Then score the match rules: If distance is 0 it gets a point, otherwise not
# Assign a percentage correctness

s1 = gpd.GeoSeries(
    labeled[["pwsid", "geometry"]]
    .loc[labeled["master_key"].isin(matches["master_key"])]
    .set_index("pwsid")
    ["geometry"])

# TIGER and MHP candidates (note that this index will not be unique)
candidate_matches = gpd.GeoDataFrame(matches
    .join(candidates[["source_system", "geometry"]], on="candidate_contributor_id")
    .rename(columns={"master_key": "pwsid"})
    .set_index("pwsid")
    [["geometry", "match_rule", "source_system"]])

# Filter to only the PWS's that appear in both series
# 7,423 match

s1 = s1.loc[s1.index.isin(candidate_matches.index)]
candidate_matches = candidate_matches.loc[candidate_matches.index.isin(s1.index)]


# This gives a couple warnings, but they're OK
# "Indexes are different" - this is because tiger_matches has duplicated indices (multiple matches to the same PWS)
# "Geometry is in a geographic CRS" - Projected CRS's will give more accurate distance results, but it's fine for our purposes.
distances = s1.distance(candidate_matches, align=True)

# Not sure what causes NA. Filter only non-NA
distances = distances[distances.notna()]
distances.name = "distance"

# re-join to the match table
candidate_matches = candidate_matches.join(distances, on="pwsid", how="inner")

# Assign a score
PROXIMITY_BUFFER = 1000
candidate_matches["score"] = candidate_matches["distance"] < PROXIMITY_BUFFER


#%%
# How did our match rules (and combos of rules) perform for TIGER?
(candidate_matches
    .loc[candidate_matches["source_system"] == "tiger"]
    .groupby(["match_rule", "source_system"])
    .agg(
        points = ("score", "sum"),
        total = ("score", "size")
    ) #type:ignore
    .eval("score = points / total")
    .sort_values("score", ascending=False))

# This suggests that our MHP matching is pretty bad.
# However, this only includes MHP's that matched to labeled bounds. And labeled bounds are likely municipalities / other big water systems, not MHP's.
# So perhaps we're filtering to only the bad matches?


#%%
candidate_matches

#%%
distances