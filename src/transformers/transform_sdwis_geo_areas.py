#%%
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb  4 11:32:27 2022

@author: jjg
"""


# Libraries
import pandas as pd
import numpy as np
import os, sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from transformers.transform_sdwis_helpers import clean_up_columns, trim_whitespace, date_type

from dotenv import load_dotenv

# %% File path and data import
load_dotenv()

data_path = os.environ["WSB_DATA_PATH"]
staging_path = os.environ["WSB_STAGING_PATH"]
sdwis_data_path = os.path.join(data_path, "sdwis")

file = "GEOGRAPHIC_AREA.CSV"

# We only use a few columns from this data. Most other columns
# are better in the primary SDWIS file.

# Though, these columns are potentially valuable, just currently unused:
# area_type_code
# tribal_code

usecols = [
    "SDWISDM_B.GEOGRAPHIC_AREA.PWSID",
    "SDWISDM_B.GEOGRAPHIC_AREA.CITY_SERVED",
    "SDWISDM_B.GEOGRAPHIC_AREA.COUNTY_SERVED"
]

geo_area = pd.read_csv(
    os.path.join(sdwis_data_path, file),
    usecols = usecols)

# %% Basic cleaning

# Remove table name from column headers
geo_area = clean_up_columns(geo_area)

# Trim whitespace
geo_area = trim_whitespace(geo_area)

# Drop duplicates
geo_area = geo_area.drop_duplicates()

# Drop fully empty columns (cities_served, counties_served -- get from other tables)
geo_area = geo_area.dropna(how='all', axis=1)


# %% Clean city_served column

geo_area["city_served"] = (geo_area["city_served"]
    .str.replace(r"\.?-\.?\s*\d{4}", "", regex=True)    # Remove "-" followed by 0 or 1 ".", 0 or more spaces, and four digits
    .str.replace(r"&apos;", "'", regex=True)            # Replace "&apos;" with "'"
    .str.replace(r"\(\s*[A-Z]\s*\)", "", regex=True)    # Replace parenthetical with single letter (plus any spaces) in it, e.g. (V) or (T)
    .str.replace(r"\s\s+", " ", regex=True))            # Replace excess whitespace within line with a single space

# Trim whitespace again
geo_area = trim_whitespace(geo_area)

#%% Deduplicate

# In a previous SDWIS download, the records with area_type_code = "TR" were
# excluded. Now they're included.

# But records with area_type_code = "TR" are contributing duplicates;
# there's often another record of a different area_type_code.

# Some notes about these duplicates:
# The ones with area_type_code = "TR" also have the tribal_code attribute populated.
# city_served and county_served is only populated when area_type_code != "TR".

# How to eliminate these duplicates?
# Since we specifically need the city_served and county_served data
# downstream, we can eliminate records that have NA's in both fields.
# This also eliminates the duplicates.

geo_area = geo_area[
    geo_area["city_served"].notna() |
    geo_area["county_served"].notna()]


# %% Raise duplication issue on key fields

if not geo_area["pwsid"].is_unique:
    raise Exception("pwsid is not unique.")
#%% 
# Save csv in staging

geo_area.to_csv(os.path.join(staging_path, "sdwis_geographic_area.csv"), index = False)
