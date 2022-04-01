#%%

import os
import numpy as np
import pandas as pd
import geopandas as gpd
import sqlalchemy as sa
from dotenv import load_dotenv

load_dotenv()

OUTPUT_PATH = os.path.join(os.environ["WSB_STAGING_PATH"], "..", "outputs")
EPSG = os.environ["WSB_EPSG"]
PROJ = os.environ["WSB_EPSG_AW"]

# Connect to local PostGIS instance
conn = sa.create_engine(os.environ["POSTGIS_CONN_STR"])


#%%
# Load up the data sources

print("Pulling in data from database...", end="")

supermodel = gpd.GeoDataFrame.from_postgis(
    "SELECT * FROM pws_contributors WHERE source_system NOT IN ('ucmr');",
    conn, geom_col="geometry")

print("done.")

sdwis = supermodel[supermodel["source_system"] == "sdwis"]
tiger = supermodel[supermodel["source_system"] == "tiger"].set_index("contributor_id")
echo = supermodel[supermodel["source_system"] == "echo"]
labeled = supermodel[supermodel["source_system"] == "labeled"]
mhp = supermodel[supermodel["source_system"] == "mhp"].set_index("contributor_id")

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

print("Read matches from database.")

#%% ##########################
# Generate some TIGER match stats
##############################

# How often do we match to multiple tigers?
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

# TIGER and MHP candidates (note that this index will not be unique)
candidate_matches = gpd.GeoDataFrame(matches
    .join(tiger["geometry"], on="candidate_contributor_id")
    .rename(columns={"master_key": "pwsid"})
    .set_index("pwsid")
    [["geometry", "match_rule", "source_system"]])

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

print("Identified best match rules based on labeled data.")

#%% ###########################
# Pick the best TIGER and MHP match
###############################

# Assign the rank back to the matches
matches_ranked = matches.join(match_ranks[["rank"]], on="match_rule", how="left")

# Sort by rank, then take the first one
# Since we only ranked the TIGER match rules, the best MHP match is selected arbitrarily
# This is fine, because multiple MHP matches are rare.
best_match = (matches_ranked
    .sort_values(["master_key", "rank"])
    .drop_duplicates(subset=["master_key", "source_system"], keep="first")
    [["master_key", "candidate_contributor_id", "source_system", "source_system_id",
    "pws_to_tiger_match_count", "tiger_to_pws_match_count"]])

print("Picked the 'best' TIGER and MHP matches.")

# For TIGER only, take the best match (ignore MHP for now)
tiger_best_match = (best_match
    .loc[best_match["source_system"] == "tiger"]
    .rename(columns={"source_system_id": "tiger_match_geoid"})
    .set_index("master_key")
    [["tiger_match_geoid", "pws_to_tiger_match_count", "tiger_to_pws_match_count"]])

print("Pulled useful information for the best TIGER match.")

mhp_best_match = (best_match
    .loc[best_match["source_system"] == "mhp"]
    .join(mhp[["geometry_lat", "geometry_long"]], on="candidate_contributor_id")
    .rename(columns={
        "source_system_id": "mhp_match_id",
        "geometry_lat": "mhp_geometry_lat",
        "geometry_long": "mhp_geometry_long"
    })
    .set_index("master_key")
    [["mhp_match_id", "mhp_geometry_lat", "mhp_geometry_long"]])

print("Pulled useful information for the best MHP match.")


#%% ##########################
# Generate the final table
##############################

output = pd.DataFrame().assign(
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

#%%
# If there's an MHP match, add matched ID and overwrite the lat/long
output = output.join(mhp_best_match, on="pwsid")

mask = output["mhp_match_id"].notna()
output.loc[mask, "geometry_lat"] = output[mask]["mhp_geometry_lat"]
output.loc[mask, "geometry_long"] = output[mask]["mhp_geometry_long"]
output.loc[mask, "geometry_quality"] = "MHP Match"

# Mark whether each one has a labeled boundary
output["has_labeled_bound"] = output["pwsid"].isin(labeled["pwsid"])

# Verify: We should still have exactly the number of pwsid's as we started with
if not (len(output) == len(sdwis)):
    raise Exception("Output was filtered or denormalized")

print("Joined several data sources into final output.")

output.head()


#%% ########################
# Save the results to a file
############################

output.to_csv(os.path.join(OUTPUT_PATH, "matched_output.csv"), index=False)

print("Saved matched_output.csv")
