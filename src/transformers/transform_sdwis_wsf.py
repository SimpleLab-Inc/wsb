#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb  4 11:10:17 2022

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

file = "WATER_SYSTEM_FACILITY.CSV"
water_system_facility = pd.read_csv(os.path.join(sdwis_data_path, file))

# %% Basic cleaning

# Remove table name from column headers
water_system_facility = clean_up_columns(water_system_facility)

# Trim whitespace
water_system_facility = trim_whitespace(water_system_facility)

# Drop duplicates
water_system_facility = water_system_facility.drop_duplicates()

# Drop fully empty columns (unnamed column from stitch file)
water_system_facility = water_system_facility.dropna(how='all', axis=1)


# %% Sanitize booleans
bool_cols = ["is_source_ind", "is_source_treated_ind"]

for i in bool_cols:
    water_system_facility[i] = water_system_facility[i].map({'N': 0, 'Y': 1, '': np.NaN, np.NaN : np.NaN})
    water_system_facility[i] = water_system_facility[i].astype('boolean')

# %% Standardize dates

date_cols = ['facility_deactivation_date','pws_deactivation_date']

# This is slow
date_type(water_system_facility, date_cols)

# %% Raise duplication issue on key fields

if (water_system_facility.duplicated(subset = ['pwsid','facility_id'], keep = False).rename("Unique").all()):
    raise Exception("pwsid and facility_id are not unique.")
    
# %% Save csv in staging

water_system_facility.to_csv(os.path.join(staging_path, "sdwis_water_system_facility.csv"), index = False)
