#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb  1 11:04:42 2022

@author: nb, jjg
"""

import os
import pandas as pd
import glob



def create_dir(path, dir):
   
    """
    A function that creates a directory for downloading data.
    
    Inputs:
        -path: file path relative to root project path
        -dir:  name of directory
    
    Output: a folder for data downloads.
    """
    
    dir_path = os.path.join(path, dir)
    
    if os.path.exists(dir_path):
        print(f'Directory {dir} exists.')
    else:
        os.mkdir(dir_path)
        print(f'Created directory {dir}.')
        
    return dir_path



def get_row_count(directory, file):

    """
    A function that counts the final rows in a given csv.
    
    Inputs:
        -directory: directory file path relative to root path
        -file:      name of file
    
    Output: row count of input file
    
    """
    path = os.path.join(directory, file)
    with open(path) as f:
        row_count = sum(1 for line in f)
    return row_count


def write_aria_download_txt(download_txt_name, path, base_filename, table_filter=None, 
                            step_size=10000, count_cur=0, count_end=200):
    """
    Write aria download text file for base_filename in path. Default file step size 
    (size of each partial download) is 10000 rows. Downloads up to count_end (default 200) files.
    Tables with more than 2MM rows require adjustments to step size and count_end.
    
    Inputs:
        -download_txt_name: name of download text file name supplied in download_with_aria()
        -path:              folder directory for a given download (e.g. data/sdwis)
        -base_filename:     filename withint download folder (e.g. WATER_SYSTEM)
        -table_filter:      optional filter to SDWIS tables, e.g. filter by state code
        -step_size:         step size of each partial download; default is 10000 rows
        -count_end:         last step in download (default is 200 files)
    
    Note: EPA Download is inclusive. If URL includes 'ROWS/0:2', 
    it downloads three rows (indices 0, 1, 2).
    """
    
    if table_filter:
        base_url = f'https://data.epa.gov/efservice/{base_filename}/{table_filter}/ROWS'
    else:
        base_url = f'https://data.epa.gov/efservice/{base_filename}/ROWS'
    
    urls_txt_path = os.path.join(path, download_txt_name)
    
    with open(urls_txt_path, 'w') as f:        
        while count_cur < count_end:
            
            row_start = count_cur * step_size
            row_end = row_start + step_size - 1
            rows = f'{str(row_start)}:{str(row_end)}'
            
            url = os.path.join(base_url, rows, 'csv')
            f.write(url + '\n')
            
            filename = f'{base_filename}_{count_cur}.csv'
            f.write(f'  out={filename}' + '\n')
            
            count_cur += 1
            
    return urls_txt_path


def download_with_aria(output_dir, filename, table_filter=None, count_end=200):
    
    """
    Create text file based on filename and base url to direct downloader. 
    Download url files using aria download text file for base_filename in path. 
    
    Inputs:
       -output_dir:        directory file path relative to root path where downloads happen
       -file:              name of file
       -table_filter:      optional filter to SDWIS tables, e.g. filter by state code
       
    Outputs: a folder of csv files in increments of step_size rows.
    
    Note: setting --auto-file-renaming=false prevents data from being appended to existing 
    downloads; a new download requires manual deletion of the previous downloads.
    """
    
    # Create subdirectory
    dir_path = create_dir(output_dir,filename)

    # Make text file of chunked aria urls and filenames
    aria_download_filename = f'aria_download_{filename}.txt'
    
    urls_txt_path = write_aria_download_txt(aria_download_filename, dir_path, filename, table_filter, count_end=200)

    # Download with aria
    os.system(f'aria2c --input-file={urls_txt_path} --dir={dir_path} --auto-file-renaming=false')


def stitch_files(filename, output_dir):
    
    """
    Create single csv file based on a folder of downloaded csvs. 
    
    Inputs:
       -output_dir:        directory file path relative to root path where downloads happen
       -filename:          name of file
       
    Outputs: a single csv file in the root project directory for use in transformers. 
    """

    extension = 'csv'
    csv_file_path = os.path.join(output_dir, filename)
    os.chdir(csv_file_path)
    
    all_filenames = [i for i in glob.glob('*.{}'.format(extension))]
    
    #combine all files in the list
    combined_csv = pd.concat([pd.read_csv(f) for f in all_filenames ])
    
    #export to csv
    combined_csv.to_csv(f"../{filename}.csv", index=False, encoding='utf-8-sig')
