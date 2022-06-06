#%%
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb  3 15:11:24 2022

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

file = "WATER_SYSTEM.CSV"
water_system = pd.read_csv(os.path.join(sdwis_data_path, file))

# %% Basic cleaning

# Remove table name from column headers
water_system = clean_up_columns(water_system)

# Trim whitespace
water_system = trim_whitespace(water_system)

# Drop duplicates
water_system = water_system.drop_duplicates()

# Drop fully empty columns (cities_served, counties_served -- get from other tables)
water_system = water_system.dropna(how='all', axis=1)


# %% Sanitize booleans
bool_cols = ["npm_candidate", "is_wholesaler_ind", \
             "is_school_or_daycare_ind", "source_water_protection_code"]

for i in bool_cols:
    water_system[i] = water_system[i].map({'N': 0, 'Y': 1, '': np.NaN, np.NaN : np.NaN})
    water_system[i] = water_system[i].astype('boolean')

# %% Standardize dates

date_cols = ['outstanding_perform_begin_date','pws_deactivation_date', \
             'source_protection_begin_date']

date_type(water_system, date_cols)

# %% Simplify zip-code column to 5 digit

water_system["zip_code"] = water_system["zip_code"].str[0:5]


# %% Raise duplication issue on key fields

if not water_system["pwsid"].is_unique:
    raise Exception("pwsid is not unique.")

# %% Save csv in staging

water_system.to_csv(os.path.join(staging_path, "sdwis_water_system.csv"), index = False)
