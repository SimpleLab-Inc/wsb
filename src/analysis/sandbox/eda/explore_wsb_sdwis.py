"""
This code explores the relationship between the state WSB data and the SDWIS data.

Updated 3/21/22

Make a dataframe that:
  - compares percentages of pwsid matching between WSB and SDWIS data
  - displays pwsid duplicate counts for states with staged WSB data
"""

#%%

import geopandas as gpd
import pandas as pd
import os
from dotenv import load_dotenv
import re


# File path and data import
load_dotenv()

staging_path = os.environ["WSB_STAGING_PATH"]

# Helper: Divides and returns a percent

def get_pc(num, denom):
    return round((num/denom)*100, 1)

#%% get list of paths/filenames for staged state wsb data
staging_file_list = [file for file in os.listdir(staging_path) if re.search(r"wsb_labeled_\w\w.gpkg", file)]
num_states = len(staging_file_list)

#%% read in sdwis data
sdwis = pd.read_csv(os.path.join(staging_path, 'sdwis_water_system.csv'))

# filter for systems with active community water systems (reduces by 90%)
sdwis = sdwis[(sdwis['pws_activity_code'] == 'A') & 
              (sdwis['pws_type_code'] == 'CWS')]

#%% compare wsb staging data with sdwis
nested_list = []

for i, staging_file in enumerate(staging_file_list):
    print(f'\rComparing WSB and SDWIS data for state {i+1}/{num_states}...', end='')
        
    # read in staged state wsb data
    # select state from sdwis data
    state_wsb = gpd.read_file(os.path.join(staging_path, staging_file))
    state = staging_file[:2].upper()
    state_sdwis = sdwis[sdwis['primacy_agency_code'] == state]
        
    # df id columns
    id_wsb = state_wsb['pwsid']
    id_sdwis = state_sdwis['pwsid']

    # df lengths
    len_wsb = len(state_wsb)
    len_sdwis = len(state_sdwis)

    # wsb id % matching to sdwis id
    wsb_matching_to_sdwis = len(state_wsb[state_wsb['pwsid'].isin(id_sdwis)])

    # sdwis id % matching to wsb id
    sdwis_matching_to_wsb = len(state_sdwis[state_sdwis['pwsid'].isin(id_wsb)])
        
    nested_list.append([state,
                        get_pc(wsb_matching_to_sdwis, len_wsb),
                        get_pc(sdwis_matching_to_wsb, len_sdwis),
                        get_pc(len_wsb, len_sdwis),
                        len(id_wsb) - len(set(id_wsb)),
                        len(id_sdwis) - len(set(id_sdwis))])

print('done.')

wsb_sdwis_matches = pd.DataFrame(nested_list, 
                                 columns=['state', 
                                          '% WSB IDs \nin SDWIS',
                                          '% SDWIS IDs \nin WSB',
                                          'WSB % size \nof SDWIS', 
                                          'WSB dup IDs', 'SDWIS dup IDs'])

#%% print table

print(wsb_sdwis_matches.to_markdown(tablefmt='pretty'))

# %%
