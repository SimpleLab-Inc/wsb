# Goal: Match Tigris places to SDWIS names

#%%

import os
import geopandas as gpd
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

pd.options.display.max_columns = None

data_path = os.environ["WSB_STAGING_PATH"]

# Bring in the FIPS -> State Abbr crosswalk
crosswalk = (pd.read_csv("../crosswalks/state_fips_to_abbr.csv")
    .set_index("code"))

#%%
tigris = gpd.read_file(data_path + "/tigris_places_clean.geojson")

#%%
keep_columns = ["STATEFP", "GEOID", "NAME", "NAMELSAD"]
tigris = tigris[keep_columns]

# Make columns lower-case
tigris.columns = [c.lower() for c in tigris.columns]

# Standardize to all-caps
tigris["statefp"] = tigris["statefp"].astype("int")

# Augment with state abbrev
tigris = tigris.join(crosswalk, on="statefp", how="inner")

# GEOID seems to be a safe unique identifier
tigris.head()

#%%

keep_columns = ["pwsid", "pws_name", "address_line1", "city_name",
    "zip_code", "primacy_agency_code", "pws_activity_code", "pws_type_code"]

sdwis: pd.DataFrame = pd.read_csv(
    data_path + "/water_system.csv",
    usecols=keep_columns)

# Filter to only active community water systems
# Starts as 400k, drops to ~50k after this filter
sdwis = (
    sdwis.loc[
        (sdwis["pws_activity_code"] == "A") &
        (sdwis["pws_type_code"] == "CWS")]
    .drop(columns=["pws_activity_code", "pws_type_code"]))

sdwis.head()


#%%

# Do we have geo's for water systems? Doesn't look like it.
# What's the difference between water_system and water_system_facility?
# Water system is 1:1 with pwsid, whereas facility lists multiple facilities w/in a system

# We could also try a spatial join if we had sdwis geocodes. But we don't.
# We could geotag them ourselves based on admin addresses. Or we could find that data source that had geocodes.

# - [ ] Q for Jess: CITIES_SERVED gets dropped because it's fully empty.
#       Transformer notes to "get from other tables." Which ones?


#%%
# Create a tokens table
tokens = (tigris[["geoid", "name", "state"]]
    .rename(columns={
        "geoid": "id"
    })
    .assign(
        source = "TIGRIS"
    ))[["source", "id", "state", "name"]]

tokens = pd.concat([
    tokens,
    sdwis[["pwsid", "primacy_agency_code", "pws_name"]]
        .rename(columns={
            "pwsid": "id",
            "primacy_agency_code": "state",
            "pws_name": "name"
        })
        .assign(
            source = "SDWIS"
        )[["source", "id", "state", "name"]]
])

tokens.sample(20)

#%%
# Tokenize!
replace = (
    "(CITY|TOWN|VILLAGE)( OF)?|WSD|HOA|WATERING POINT|LLC|PWD|MHP" +
    "|(PUBLIC |RURAL )?WATER (DISTRICT|COMPANY|SYSTEM|WORKS|DEPARTMENT|DEPT)|SUBDIVISION"
    "|MUNICIPAL UTILITIES"
)

tokens["name_tkn"] = (tokens["name"]
    .str.upper() # Standardize to upper-case
    .str.replace(fr"\b({replace})\b", "", regex=True)
    .str.replace(r"[^\w ]", " ", regex=True) # Replace non-word characters
    .str.replace(r"\s\s+", " ", regex=True) # Normalize spaces
    .str.strip())

#%%

tokens_tigris = tokens[tokens["source"] == "TIGRIS"]
tokens_sdwis = tokens[tokens["source"] == "SDWIS"]

# 10836 matches
# How is it that matching got worse? Oh it's those \b's
tokens_tigris.merge(
    tokens_sdwis,
    on=["state", "name_tkn"],
    how="inner")

#%%
# Export a sorted list of tokens for manual review
tokens.sort_values(["state", "name"]).to_excel("match_review.xlsx")
