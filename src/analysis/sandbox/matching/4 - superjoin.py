#%%

import os
import numpy as np
import pandas as pd
import geopandas as gpd
import sqlalchemy as sa
from dotenv import load_dotenv

load_dotenv()

DATA_PATH = os.environ["WSB_STAGING_PATH"] + "/../outputs"
EPSG = os.environ["WSB_EPSG"]
PROJ = os.environ["WSB_EPSG_AW"]

# Connect to local PostGIS instance
conn = sa.create_engine(os.environ["POSTGIS_CONN_STR"])


#%%
# Load up the data sources

supermodel = gpd.GeoDataFrame.from_postgis(
    "SELECT * FROM pws_contributors WHERE source_system NOT IN ('ucmr');",
    conn, geom_col="geometry")

sdwis = supermodel[supermodel["source_system"] == "sdwis"]
tiger = supermodel[supermodel["source_system"] == "tiger"].set_index("contributor_id")
echo = supermodel[supermodel["source_system"] == "echo"]
labeled = supermodel[supermodel["source_system"] == "labeled"]
#%%
matches = pd.read_sql("""
    SELECT
        m.master_key,
        m.candidate_contributor_id,
        m.match_rule,
        c.source_system,
        c.source_system_id
    FROM matches m
    JOIN pws_contributors c ON m.candidate_contributor_id = c.contributor_id;
    """, conn)

#%% ##########################
# Pick the best TIGER match
##############################

"""
We'll compare the matches to the labeled data to determine which match
rules (and combos of rules) are most effective. Rank our matches based
on that, and select the top one.
"""

# First, a check: How often do we match to multiple tigers?
pws_to_tiger_match_counts = (matches
    .loc[matches["source_system"] == "tiger"]
    .groupby("master_key")
    .size())

pws_to_tiger_match_counts.name = "pws_to_tiger_match_count"

# Let's also do it the other direction
tiger_to_pws_match_counts = (matches
    .loc[matches["source_system"] == "tiger"]
    .groupby("candidate_contributor_id")
    .size())

tiger_to_pws_match_counts.name = "tiger_to_pws_match_count"

# Augment matches with these TIGER match stats
matches = (matches
    .join(pws_to_tiger_match_counts, on="master_key")
    .join(tiger_to_pws_match_counts, on="candidate_contributor_id"))

# 1850 situations with > 1 match
print(f"{(pws_to_tiger_match_counts > 1).sum()} PWS's matched to multiple TIGERs")

# 3631 TIGERs matched to multiple PWSs
print(f"{(tiger_to_pws_match_counts > 1).sum()} TIGER's matched to multiple PWS's")

#%%

# Get a series with the labeled geometry for each PWS
s1 = gpd.GeoSeries(
    labeled[["pwsid", "geometry"]]
    .loc[labeled["master_key"].isin(matches["master_key"])]
    .set_index("pwsid")
    ["geometry"])

# TIGER and MHP candidates (note that this index will not be unique)
candidate_matches = gpd.GeoDataFrame(matches
    .join(tiger["geometry"], on="candidate_contributor_id")
    .rename(columns={"master_key": "pwsid"})
    .set_index("pwsid")
    [["geometry", "match_rule", "source_system"]])

#%%

# Filter to only the PWS's that appear in both series
# 7,423 match

s1 = s1.loc[s1.index.isin(candidate_matches.index)]
candidate_matches = candidate_matches.loc[candidate_matches.index.isin(s1.index)]

# Switch to a projected CRS
s1 = s1.to_crs(PROJ)
candidate_matches = candidate_matches.to_crs(PROJ)

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
PROXIMITY_BUFFER = 1000 # Meters
candidate_matches["score"] = candidate_matches["distance"] < PROXIMITY_BUFFER

#%%

# Assign a "rank" to each match rule and combo of match rules
match_ranks = (candidate_matches
    .loc[candidate_matches["source_system"] == "tiger"]
    .groupby(["match_rule"])
    .agg(
        points = ("score", "sum"),
        total = ("score", "size")
    )) #type:ignore

match_ranks["score"] = match_ranks["points"] / match_ranks["total"]
match_ranks = match_ranks.sort_values("score", ascending=False)
match_ranks["rank"] = np.arange(len(match_ranks))

match_ranks

#%%

# Assign the rank back to the matches
matches = matches.join(match_ranks[["rank"]], on="match_rule", how="left")

matches.head()

#%%

# Sort by rank, then take the first one
match_dedupe = (matches
    .sort_values(["master_key", "rank"])
    .drop_duplicates(subset=["master_key", "source_system"], keep="first")
    [["master_key", "candidate_contributor_id", "source_system", "source_system_id",
    "pws_to_tiger_match_count", "tiger_to_pws_match_count"]])

# For TIGER only, take the best match (ignore MHP for now)
tiger_best_match = (match_dedupe
    .loc[match_dedupe["source_system"] == "tiger"]
    .rename(columns={
        "master_key": "pwsid",
        "source_system_id": "tiger_match_geoid"
    })
    .set_index("pwsid")
    [["tiger_match_geoid", "pws_to_tiger_match_count", "tiger_to_pws_match_count"]])


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
centroid_lat             | Proposed: (1) MHP, (2) UCMR, (3) Echo, in order
centroid_long            | Proposed: (1) MHP, (2) UCMR, (3) Echo, in order
state_code               | SDWIS
county_served            | SDWIS
city_served              | SDWIS
population_served        | SDWIS
connections              | SDWIS
primacy_agency_code      | SDWIS
service_area_type_code   | SDWIS
"""

output = pd.DataFrame().assign(
    master_key                 = sdwis["master_key"],
    pwsid                      = sdwis["pwsid"],
    pws_name                   = sdwis["name"],
    primacy_agency_code        = sdwis["primacy_agency_code"],
    state_code                 = sdwis["state"],
    city_served                = sdwis["city_served"],
    county_served              = sdwis["county"],
    population_served_count    = sdwis["population_served_count"],
    service_connections_count  = sdwis["service_connections_count"],
    service_area_type_code     = sdwis["service_area_type_code"],
    owner_type_code            = sdwis["owner_type_code"]
)

# Supplement with echo centroid
# TODO later - Pick the best lat/long from echo, mhp, or UCMR

output = (output
    .merge(echo[[
        "pwsid",
        "geometry_lat",
        "geometry_long",
        "geometry_quality",
        #"geometry"
        # Does the model need these extra columns? I can pull them in from the raw file if so...
        # "fac_collection_method",
        # "fac_street",
        # "fac_city",
        # "fac_state",
        # "fac_zip",
        # "fac_county",
        # 'fac_reference_point',
        # 'fac_accuracy_meters',
        # 'fac_indian_cntry_flg',
        # 'fac_percent_minority',
        # 'fac_pop_den',
        # 'ejscreen_flag_us'
    ]], on="pwsid", how="left"))

# Add in the TIGER geoid and pws --> TIGER match counts
output = output.join(tiger_best_match, on="pwsid")

# Mark whether each one has a labeled boundary
output["has_labeled_bound"] = output["pwsid"].isin(labeled["pwsid"])

# Verify: We should still have exactly the number of pwsid's as we started with
if not (len(output) == len(sdwis)):
    raise Exception("Output was filtered or denormalized")

output.head()


#%%
# Save the results
output.to_csv(DATA_PATH + "/matched_output.csv", index=False)

#%%
# Stat: Total population with either a tiger match or a labeled boundary?

population_covered = int(output[output["tiger_match_geoid"].notna() | output["has_labeled_bound"]]["population_served_count"].sum())
total_population = int(output["population_served_count"].sum())

print(
    f"Total population served: {population_covered:,} " +
    f"({(float(population_covered) / total_population) * 100:.1f}%)")
