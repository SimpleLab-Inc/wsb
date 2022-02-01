#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb  1 11:06:58 2022

@author: nb, jjg
"""


# Libraries
import os
from downloaders.download_helpers import create_dir, get_row_count
from downloaders.download_helpers import download_with_aria, stitch_files


#%%
# Create file directory
path = "data/"
directory = 'sdwis'

# Set output directory
create_dir(path, directory)

output_dir = "data/sdwis/"

#%% Download smaller files to sdwis directory

# SERVICE_AREA, GEOGRAPHIC_AREA

filenames = ['SERVICE_AREA', 'GEOGRAPHIC_AREA']


for filename in filenames:
    print(f'Downloading {filename}')
    
    base_url = f'https://data.epa.gov/efservice/{filename}/ROWS/0:100000000/csv'
    
    os.system(f'aria2c --out={filename}.csv --dir={output_dir} {base_url} --auto-file-renaming=false')
    
    # Print row count
    row_count = get_row_count(output_dir, f'{filename}.csv')
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

download_with_aria(output_dir,filename)

# Stitch and count rows
if not os.path.exists(os.path.join(output_dir, f'{filename}.csv')):
    stitch_files(filename, output_dir)
    directory = os.path.join(output_dir, f'{filename}/')
    row_count = get_row_count(output_dir, f'{filename}.csv')
    print(f'Row count of {filename}.csv: {row_count}')


#%% Download WATER_SYSTEM_FACILITY
filename = 'WATER_SYSTEM_FACILITY'

download_with_aria(output_dir, filename)
 
print(f'Row count of {filename}.csv: {row_count}')

# Stitch and count rows

if not os.path.exists(os.path.join(output_dir, f'{filename}.csv')):
    stitch_files(filename, output_dir)   
    directory = os.path.join(output_dir, f'{filename}/')
    row_count = get_row_count(output_dir, f'{filename}.csv')
    print(f'Row count of {filename}.csv: {row_count}')



