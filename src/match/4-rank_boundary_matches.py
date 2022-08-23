#%%

import os
import numpy as np
import pandas as pd
import sqlalchemy as sa
from dotenv import load_dotenv

from match.match_scorer import MatchScorer

load_dotenv()

STAGING_PATH = os.environ["WSB_STAGING_PATH"]
EPSG = os.environ["WSB_EPSG"]
PROJ = os.environ["WSB_EPSG_AW"]

# Connect to local PostGIS instance
conn = sa.create_engine(os.environ["POSTGIS_CONN_STR"])

#%%
matches = pd.read_sql("""
    SELECT
        m.master_key,
        m.candidate_contributor_id,
        m.match_rule,
        s.name                      AS sdwis_name,
        s.population_served_count   AS sdwis_pop,
        c.name                      AS tiger_name,
        c.population_served_count   AS tiger_pop
    FROM matches m
    JOIN pws_contributors c ON m.candidate_contributor_id = c.contributor_id AND c.source_system = 'tiger'
    JOIN pws_contributors s ON s.master_key = m.master_key AND s.source_system = 'sdwis';
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

# 1850 situations with > 1 match
print(f"{(pws_to_tiger_match_counts > 1).sum()} PWS's matched to multiple TIGERs")

# 3631 TIGERs matched to multiple PWSs
print(f"{(tiger_to_pws_match_counts > 1).sum()} TIGER's matched to multiple PWS's")

#%% #########################
# Figure out our strongest match rules
#############################
scorer = MatchScorer()
scored_matches = scorer.score_tiger_matches(matches)

#%%
"""
Use the "scored" data to determine which rules (and combos of rules)
are most effective.
"""

# Assign a "rank" to each match rule and combo of match rules
match_rule_ranks = (matches
    .join(scored_matches, on=["master_key", "candidate_contributor_id"])
    .groupby(["match_rule"])
    .agg(
        points = ("score", "sum"),
        total = ("score", "size")
    )) #type:ignore

match_rule_ranks["score"] = match_rule_ranks["points"] / match_rule_ranks["total"]
match_rule_ranks = match_rule_ranks.sort_values("score", ascending=False)
match_rule_ranks["match_rule_rank"] = np.arange(len(match_rule_ranks))

print("Identified best match rules based on labeled data.")

#%% ###########################
# Rank all PWS<->TIGER matches
###############################

# Assign the match rule ranks back to the matches
matches_ranked = matches.join(
    match_rule_ranks[["match_rule_rank"]], on="match_rule", how="left")

# Flag any that have name matches
matches_ranked["name_match"] = matches.apply(lambda x: x["tiger_name"] in x["sdwis_name"], axis=1)

# Flag the best population within each TIGER match set
# (Note this should be done AFTER removing the best PWS->TIGER, if we're doing that)
matches_ranked["pop_diff"] = abs(matches["tiger_pop"] - matches["sdwis_pop"])

# To get PWS<->TIGER to be 1:1, we'll rank on different metrics
# and then select the top one. We need to do this twice:
# Once to make PWS->Tiger N:1 and then to make Tiger->PWS 1:1

#%%
# Through experimentation, this seemed to be the best ranking:
# name_match, match_rule_rank, pop_diff
# and selecting within the candidate_contributor groups first,
# master_key groups second.

# Assign numeric ranks to every match
matches_ranked = (matches_ranked
    .sort_values(
        ["name_match", "match_rule_rank", "pop_diff"],
        ascending=[False, True, True])
    # Re-number and bring that index into the df
    # This gives us a simple column to rank on
    .reset_index(drop=True)
    .reset_index(drop=False)
    .rename(columns={"index": "overall_rank"}))

# I guess this is technically unnecessary, cause it's equivalent to sorting on overall_rank...
# but maybe it make things a little clearer?
matches_ranked["master_group_ranking"] = \
    (matches_ranked
        .groupby("master_key")
        ["overall_rank"]
        .rank("dense")
        .astype("int"))

#%%
# Identify the 1-1 matches using the overall_rank
best_matches = (matches_ranked
    .sort_values(["overall_rank"])
    .drop_duplicates(subset="candidate_contributor_id", keep="first")
    .drop_duplicates(subset="master_key", keep="first")).index

matches_ranked["best_match"] = matches_ranked.index.isin(best_matches)

#%%

print("Scoring 1:1 matches...")

# Score it. how'd we do?
scored_best_matches = scorer.score_tiger_matches(
    matches_ranked
        .loc[matches_ranked["best_match"]]
        [["master_key", "candidate_contributor_id"]])

# ~ 96%
score = scored_best_matches["score"].sum() * 100 / len(scored_best_matches)

print(f"Boundary match score: {score:.2f}")

#%%
matches_ranked.to_sql("matches_ranked", conn, if_exists="replace", index=False)
