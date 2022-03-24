#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Libraries
import pandas as pd
import numpy as np
import os, sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from transform_sdwis_helpers import clean_up_columns, trim_whitespace

from dotenv import load_dotenv

# %% File path and data import
load_dotenv()

data_path = os.environ["WSB_DATA_PATH"]
staging_path = os.environ["WSB_STAGING_PATH"]
echo_data_path = os.path.join(data_path, "echo")

file = "ECHO_EXPORTER.CSV"

col_list = ['REGISTRY_ID', 'FAC_NAME', 'FAC_NAME', 'FAC_STREET', 'FAC_CITY', 
    'FAC_STATE', 'FAC_ZIP', 'FAC_COUNTY', 'FAC_FIPS_CODE', 'FAC_LAT', 'FAC_INDIAN_CNTRY_FLG', 
    'FAC_FEDERAL_FLG', 'FAC_LONG', 'FAC_COLLECTION_METHOD', 'FAC_REFERENCE_POINT', 
    'FAC_ACCURACY_METERS', 'FAC_DERIVED_HUC', 'FAC_MAJOR_FLAG', 'FAC_ACTIVE_FLAG', 
    'FAC_QTRS_WITH_NC', 'SDWIS_FLAG', 'SDWA_IDS', 'SDWA_SYSTEM_TYPES', 
    'SDWA_INFORMAL_COUNT', 'SDWA_FORMAL_ACTION_COUNT', 'SDWA_COMPLIANCE_STATUS', 
    'SDWA_SNC_FLAG', 'FAC_DERIVED_TRIBES', 'FAC_DERIVED_HUC', 'FAC_DERIVED_WBD', 
    'FAC_DERIVED_STCTY_FIPS', 'FAC_DERIVED_ZIP', 'FAC_DERIVED_CD113', 'FAC_DERIVED_CB2010', 
    'FAC_PERCENT_MINORITY', 'FAC_POP_DEN', 'EJSCREEN_FLAG_US']

# Pull in ECHO data
echo = pd.read_csv(os.path.join(echo_data_path, file), low_memory = False, usecols = col_list)

#%% PREPARE DATA

# Adjust column headers and drop empty columns
echo = clean_up_columns(echo)

# Trim white space
echo = trim_whitespace(echo)

# drop duplicates 
echo = echo.drop_duplicates()

# Drop any null SDWA_IDS
echo = echo.dropna(subset = ['sdwa_ids'])

# The sdwa_ids column contains multiple space-delimited PWSIDs. Turn them into Python lists.
echo["sdwa_ids"] = echo["sdwa_ids"].str.split()

# Now duplicate rows where we have multiple ID's and rename to pwsid
echo = echo.explode("sdwa_ids").rename(columns={"sdwa_ids": "pwsid"})


#%% Sanitize booleans
# Map `N` to `False` and `Y` to `True`.
bool_cols = ['fac_major_flag', 'fac_active_flag', 
             'sdwis_flag', 'sdwa_snc_flag', 'fac_indian_cntry_flg',
             'fac_federal_flg', 'ejscreen_flag_us']

for i in bool_cols:
    echo[i] = echo[i].map({'N': 0, 'Y': 1, '': np.NaN, np.NaN : np.NaN})
    echo[i] = echo[i].astype('boolean')

# %%

echo.to_csv(os.path.join(staging_path, "echo.csv"), index = False)

