#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb  1 11:06:58 2022

@author: nb, jjg
"""


# Libraries
import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from downloaders.download_helpers import create_dir, get_row_count
from downloaders.download_helpers import download_with_aria, stitch_files
from dotenv import load_dotenv

load_dotenv()

#%%
# Create file directory
data_path = os.environ["WSB_DATA_PATH"]
directory = 'sdwis'

# Set output directory
create_dir(data_path, directory)

sdwis_data_path = os.path.join(data_path, "sdwis")

#%% Download smaller files to sdwis directory

# SERVICE_AREA, GEOGRAPHIC_AREA

filenames = ['SERVICE_AREA', 'GEOGRAPHIC_AREA']


for filename in filenames:
    if os.path.exists(os.path.join(sdwis_data_path, filename + ".csv")):
        pass
        print(f"{filename}.csv exists, skipping download.")
        
    else:    
        print(f'Downloading {filename}')
        
        base_url = f'https://data.epa.gov/efservice/{filename}/ROWS/0:100000000/csv'
        
        os.system(f'aria2c --out={filename}.csv --dir={sdwis_data_path} {base_url} --auto-file-renaming=false')
        
        # Print row count
        row_count = get_row_count(sdwis_data_path, f'{filename}.csv')
        print(f'Row count of {filename}.csv: {row_count}')


#%% Download larger files
# While the smaller files above work without timing out, SDWIS has a 10K query limit
# on tables; the following script could be used for the above tables as well, but currently
# are limited to the larger of the 4 files to avoid time outs

# Current working assumption is that there are no more than 2MM rows for 
# water_system and water_system_facility; this could theoretically change over time
# and the analyst would need to adjust the default value


#%% Download WATER_SYSTEM
filename = 'WATER_SYSTEM'


if os.path.exists(os.path.join(sdwis_data_path, filename + "/")): 
    pass
    print(f"{filename} folder exists, skipping download.")
        
else:   
    download_with_aria(sdwis_data_path,filename, count_end=200)

# Stitch and count rows
if not os.path.exists(os.path.join(sdwis_data_path, f'{filename}.csv')):
    stitch_files(filename, sdwis_data_path)
    directory = os.path.join(sdwis_data_path, f'{filename}/')
    row_count = get_row_count(sdwis_data_path, f'{filename}.csv')
    print(f'Row count of {filename}.csv: {row_count}')

else:
    print(f'{filename}.csv already exists and will not re-stitch.')
