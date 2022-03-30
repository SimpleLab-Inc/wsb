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

from transform_sdwis_helpers import clean_up_columns, trim_whitespace, date_type

from dotenv import load_dotenv

# %% File path and data import
load_dotenv()

data_path = os.environ["WSB_DATA_PATH"]
staging_path = os.environ["WSB_STAGING_PATH"]
sdwis_data_path = os.path.join(data_path, "sdwis")

file = "GEOGRAPHIC_AREA.CSV"
geo_area = pd.read_csv(os.path.join(sdwis_data_path, file))

# %% Basic cleaning

# Remove table name from column headers
geo_area = clean_up_columns(geo_area)

# Trim whitespace
geo_area = trim_whitespace(geo_area)

# Drop duplicates
geo_area = geo_area.drop_duplicates()

# Drop fully empty columns (cities_served, counties_served -- get from other tables)
geo_area = geo_area.dropna(how='all', axis=1)


# %% Clean state served column from pwsid

geo_area["state_served_temp"] = geo_area["pwsid"].str[0:2].astype("str")

diffs = geo_area.loc[geo_area["state_served"] != geo_area["state_served_temp"]]

geo_area["state_served_fin"] = np.where(geo_area["state_served"].isna(), \
                                      geo_area["state_served_temp"], geo_area["state_served"])

geo_area = geo_area.drop(columns = ["state_served_temp", "state_served"]) \
                .rename(columns = {"state_served_fin": "state_served"})
                
# %% Clean city_served column

# Remove "-" followed by 0 or 1 ".", 0 or more spaces, and four digits
geo_area["city_served"] = geo_area["city_served"].str.replace("\.?-\.?\s*\d{4}", 
                                                              "", regex=True)
# Replace "&apos;" with "'"
geo_area["city_served"] = geo_area["city_served"].str.replace("&apos;", 
                                                              "'", regex=True)

# %% Raise duplication issue on key fields

if (geo_area.duplicated(subset = ['pwsid'], keep = False).rename("Unique").all()):
    raise Exception("pwsid is not unique.")
     
 # %% Save csv in staging

geo_area.to_csv(os.path.join(staging_path, "sdwis_geographic_area.csv"), index = False)
