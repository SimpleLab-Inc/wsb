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


#%%
# Load up the data sources

supermodel = gpd.GeoDataFrame.from_postgis(
    "SELECT * FROM pws_contributors WHERE source_system NOT IN ('ucmr');",
    conn, geom_col="geometry")

sdwis = supermodel[supermodel["source_system"] == "sdwis"]
tiger = supermodel[supermodel["source_system"] == "tiger"].set_index("master_key")
echo = supermodel[supermodel["source_system"] == "echo"]

matches = pd.read_sql("SELECT * FROM matches;", conn)

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

output.head()

#%% #########################
# Pick best match
#############################

"""
# For sdwis --> tiger, deduplicate by distance

# First, join the output to TIGER via the match table

(output
    .merge(matches, left_on="pwsid", right_on="master_key_x")
    .merge(tiger[["master_key", "source_system_id", "geometry"]], left_on="master_key_y", right_on="master_key"))

# K, now calculate the differences in the geometries

#%%

# I need to create two geoseries with the same index
# Let's make pwsid the index?

s1 = gpd.GeoSeries(
        output[["pwsid", "geometry"]]
        .loc[output["master_key"].isin(matches["master_key_x"])]
        .set_index("pwsid")
        ["geometry"])

#%%

# TIGER candidates (note that this index will not be unique)
s2 = gpd.GeoSeries(matches
    .join(tiger["geometry"], on="master_key_y")
    .rename(columns={"master_key_x": "pwsid"})
    .set_index("pwsid")
    ["geometry"])

#%%

# Augment each match with its distance.
# Of course, spatial matches will always be distance 0.
# So spatial matches will always beat name matches.
distances = s1.distance(s2, align=True)
"""
#%%

# Know what....for now I'll just do arbitrary pick-one per source system
match_dedupe = (matches
    .merge(
        supermodel[["contributor_id", "source_system", "source_system_id"]],
        left_on="candidate_contributor_id", right_on="contributor_id")
    .drop_duplicates(subset=["master_key", "source_system"], keep="first")
    [["master_key", "candidate_contributor_id", "source_system", "source_system_id"]])

tiger_best_match = (match_dedupe
    .loc[match_dedupe["source_system"] == "tiger"]
    .rename(columns={
        "master_key": "pwsid",
        "source_system_id": "tiger_match_geoid"
    })
    .set_index("pwsid")
    ["tiger_match_geoid"])

# Augment the output with the geoid
output = output.join(tiger_best_match, on="pwsid")

# For now, let's ignore the MHP's

# Verify: We should still have exactly the number of pwsid's as we started with
if not (len(output) == len(sdwis)):
    raise Exception("Output was filtered or denormalized")

#%%
# Mark whether each one has a labeled boundary

labeled_pwsids = supermodel[supermodel["source_system"] == "labeled"]["pwsid"]

output["has_labeled_bound"] = output["pwsid"].isin(labeled_pwsids)

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
