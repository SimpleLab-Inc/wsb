#%%

import os
from typing import List, Optional
import pandas as pd
import geopandas as gpd
from dotenv import load_dotenv
import sqlalchemy as sa

load_dotenv()

pd.options.display.max_columns = None

# Connect to local PostGIS instance
conn = sa.create_engine(os.environ["POSTGIS_CONN_STR"])


#%%
# Load up the supermodel

print("Pulling data from the database...", end=None)
supermodel = gpd.GeoDataFrame.from_postgis(
    "SELECT * FROM pws_contributors;", conn, geom_col="geometry")
print("done.")

#%% ##############################
# More Cleansing (or this could move to script #1, or into the tokenization)
##################################

# These words usually indicate a mobile home park
regex = r"\b(?:MOBILE|TRAILER|MHP|TP|CAMPGROUND|RV)\b"

supermodel["likely_mhp"] = (
    (supermodel["source_system"] == "mhp") |
    # If ANY of systems with the same PWSID have a name that indicates likely MHP,
    # then mark the whole set as likely MHP
    supermodel["pwsid"].isin(
        supermodel[
            supermodel["source_system"].isin(["echo", "sdwis", "frs"]) &
            supermodel["name"].notna() &
            supermodel["name"].fillna("").str.contains(regex, regex=True)
        ]["pwsid"]
    )
)

# These words often (but not always) indicate a mobile home park
regex = r"\b(?:VILLAGE|MANOR|ACRES|ESTATES)\b"

supermodel["possible_mhp"] = (
    (supermodel["source_system"] == "mhp") |
    (supermodel["likely_mhp"]) |
    supermodel["pwsid"].isin(
        supermodel[
            supermodel["source_system"].isin(["echo", "sdwis", "frs"]) &
            supermodel["name"].notna() &
            supermodel["name"].fillna("").str.contains(regex, regex=True)
        ]["pwsid"]
    ))

print("Labeled likely and possible MHP's.")


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
        .str.replace(fr"\b({replace})\b", "", regex=True)   # Remove water and utility words
        .str.replace(r"[^\w ]", " ", regex=True)            # Replace non-word characters
        .str.replace(r"\s\s+", " ", regex=True)             # Normalize spaces
        .str.strip()                                        # Remove leading and trailing spaces
        .replace({"": pd.NA}))                              # If left with nothing, null it out

def tokenize_mhp_name(series) -> pd.Series:
    
    # NOTE: It might be better to do standardizations instead of replacing with empty
    replace = (
        r"MOBILE (HOME|TRAILER)( PARK| PK)?|MOBILE (ESTATE(S?)|VILLAGE|MANOR|COURT|VILLA|HAVEN|RANCH|LODGE|RESORT)|" + 
        r"MOBILE(HOME|LODGE)|MOBILE( PARK| PK| COM(MUNITY)?)|MHP"
    )

    return (series
        .str.upper() # Standardize to upper-case
        .str.replace(fr"\b({replace})\b", "", regex=True)   # Remove MHP words
        .str.replace(r"[^\w ]", " ", regex=True)            # Replace non-word characters
        .str.replace(r"\s\s+", " ", regex=True)             # Normalize spaces
        .str.strip()
        .replace({"": pd.NA}))                              # If left with nothing, null it out


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
        [["master_key_x", "contributor_id_x", "contributor_id_y"]]
        .rename(columns={"master_key_x": "master_key"}))

    matches["match_rule"] = match_rule

    return matches

#%% ##############################
# Create a token table and apply standardizations
##################################

tokens = supermodel[[
    "source_system", "contributor_id", "master_key", "state", "name", "city_served",
    "address_line_1", "city", "zip", "county", 
    "geometry", "centroid_quality", "likely_mhp", "possible_mhp"
    ]].copy()

tokens["name_tkn"] = tokenize_ws_name(tokens["name"])
tokens["mhp_name_tkn"] = tokenize_mhp_name(tokens["name"])

print("Generated token table.")

# In general, we'll be matching sdwis/echo to tiger
# SDWIS, ECHO, and FRS are already matched - they'll go on the left.
# TIGER needs to be matched - it's on the right.
# UCMR is already matched, and doesn't add any helpful matching criteria, so we exclude it. Exception: IF it's high quality, it might be helpful in spatial matching to TIGER?

#%%

# Stash the tokens WITHOUT geometry (for speed)
# These are used in reporting later
conn.execute("DROP TABLE IF EXISTS tokens;")
tokens.drop(columns="geometry").to_sql("tokens", conn, index=False)

print("Saved token table to database (for later analysis)")

#%% #########################
# Rule: Match on state + name to SDWIS/ECHO/FRS -> TIGER
# 23,286 matches

new_matches = run_match(
    "state+name_tiger",
    ["state", "name_tkn"],
    left_mask = (
        tokens["source_system"].isin(["sdwis", "echo", "frs"]) &
        tokens["state"].notna() &
        tokens["name_tkn"].notna() &
        (~tokens["likely_mhp"])),
    right_mask = (
        tokens["source_system"].isin(["tiger"]) &
        tokens["state"].notna() &
        tokens["name_tkn"].notna()))

print(f"State+Name to Tiger matches: {len(new_matches)}")

matches = new_matches

#%% #########################
# Rule: Match on state + name to MHP
# 1,875 matches

new_matches = run_match(
    "state+name_mhp",
    ["state", "name_tkn"],
    left_mask = (
        tokens["source_system"].isin(["sdwis", "echo", "frs"]) &
        tokens["state"].notna() &
        tokens["name_tkn"].notna()),
    right_mask = (
        tokens["source_system"].isin(["mhp"]) &
        tokens["state"].notna() &
        tokens["name_tkn"].notna()))

print(f"State+Name MHP matches: {len(new_matches)}")

matches = pd.concat([matches, new_matches])


#%% #########################
# Rule: Spatial matches
# 11,941 matches between echo/frs and tiger
# (Down from 22,200 before excluding state, county, and zip centroids)

left_mask = (
    tokens["source_system"].isin(["echo", "frs"]) &
    (~tokens["likely_mhp"]) &
    (~tokens["centroid_quality"].isin([
        "STATE CENTROID",
        "COUNTY CENTROID",
        "ZIP CODE CENTROID"
    ])))

right_mask = tokens["source_system"].isin(["tiger"])

new_matches = (tokens[left_mask]
    .sjoin(tokens[right_mask], lsuffix="x", rsuffix="y")
    [["master_key_x", "contributor_id_x", "contributor_id_y"]]
    .rename(columns={"master_key_x": "master_key"})
    .assign(match_rule="spatial"))


# Also require that the states match in both systems

contributor_state = tokens.set_index("contributor_id")["state"]

new_matches_with_states = (new_matches
    .join(contributor_state, on="contributor_id_x")
    .join(contributor_state, on="contributor_id_y", rsuffix="_y"))

new_matches = new_matches[new_matches_with_states["state"] == new_matches_with_states["state_y"]]

print(f"Spatial matches: {len(new_matches)}")

matches = pd.concat([matches, new_matches])

#%% #########################
# Rule: match state+city_served to state&name
# 16,265 matches

new_matches = run_match(
    "state+city_served",
    left_on = ["state", "city_served"],
    right_on = ["state", "name_tkn"],
    left_mask = (
        tokens["source_system"].isin(["sdwis"]) &
        tokens["state"].notna() &
        tokens["city_served"].notna() &
        (~tokens["likely_mhp"])),
    right_mask = (
        tokens["source_system"].isin(["tiger"]) &
        tokens["state"].notna() &
        tokens["name_tkn"].notna()))

print(f"Match on city_served: {len(new_matches)}")

matches = pd.concat([matches, new_matches])

#%% #########################
# Rule: UCMR to TIGER Spatial matches
# 2,999 matches

left_mask = tokens["source_system"].isin(["ucmr"])
right_mask = tokens["source_system"].isin(["tiger"])

new_matches = (tokens[left_mask]
    .sjoin(tokens[right_mask], lsuffix="x", rsuffix="y")
    [["master_key_x", "contributor_id_x", "contributor_id_y"]]
    .rename(columns={"master_key_x": "master_key"})
    .assign(match_rule="ucmr_spatial"))

print(f"UCMR spatial matches: {len(new_matches)}")

matches = pd.concat([matches, new_matches])

#%% #########################
# Rule: match MHP's by tokenized name
# 20897 matches. Not great, but then again, not all MHP's will have water systems.

# We get a few hundred more matches if we exclude the county, and it *seems* like
# MHP names should be relatively unique within the state...but I spot checked
# some and wasn't 100% convinced. So I'm being conservative and requiring county.

new_matches = run_match(
    "state+mhp_name",
    ["state", "mhp_name_tkn", "county"],
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

#%% #########################
# Rule: match MHP's by state + city + address

# Unfortunately, half of the "MHP" system has no names, so we try this rule.
# 228 matches

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

#%% ################################
# Deduplicate matches to PWSID <-> contributor_id pairs.
####################################

# The left side contains known PWS's and can be deduplicated by crosswalking to the master_key (pwsid)
# The right side contains unknown (candidate) matches and could stay as an contributor_id

mk_matches = (matches
    .rename(columns={"contributor_id_y": "candidate_contributor_id"}) #type:ignore
    [["master_key", "candidate_contributor_id", "match_rule"]])

# Deduplicate
mk_matches = (mk_matches
    .groupby(["master_key", "candidate_contributor_id"])["match_rule"]
    .apply(lambda x: list(pd.Series.unique(x)))
    .reset_index())


#%%

# Save the matches back to the database
conn.execute("DROP TABLE IF EXISTS match_contributors;")
matches.to_sql("match_contributors", conn, index=False)

# Save the matches back to the database
conn.execute("DROP TABLE IF EXISTS matches;")
mk_matches.to_sql("matches", conn, index=False)