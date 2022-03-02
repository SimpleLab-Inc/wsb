#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Feb 11 16:54:19 2022

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

file = "SERVICE_AREA.CSV"
service_area = pd.read_csv(os.path.join(sdwis_data_path, file))

# %% Basic cleaning

# Remove table name from column headers
service_area = clean_up_columns(service_area)

# Trim whitespace
service_area = trim_whitespace(service_area)

# Drop duplicates
service_area = service_area.drop_duplicates()

# Drop fully empty columns (cities_served, counties_served -- get from other tables)
service_area = service_area.dropna(how='all', axis=1)


# %% Sanitize booleans
bool_cols = ["is_primary_service_area_code"]

for i in bool_cols:
    service_area[i] = service_area[i].map({'N': 0, 'Y': 1, '': np.NaN, np.NaN : np.NaN})
    service_area[i] = service_area[i].astype('boolean')


# %% Raise duplication issue on key fields

if (service_area.duplicated(subset = ['pwsid'], keep = False).rename("Unique").all()):
    raise Exception("pwsid is not unique.")

# %% Save csv in staging

service_area.to_csv(os.path.join(staging_path, "sdwis_service_area.csv"), index = False)
