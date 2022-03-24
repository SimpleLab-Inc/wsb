# Overview and contributor guide for downloaders
_________________

_Last updated 2022-03-23_  

## List of downloaders
_________________

- `states/download_%_wsb.R`: Water system boundary data for `%` state
- `download_echo.R`: ECHO admin data
- `download_frs.R`: FRS centroids
- `download_mhp.R`: Mobile home parks point data
- `download_sdwis.py`: SDWIS data
- `download_tigris_ne.R`: TIGRIS places and Natural Earth coastline
- `download_ucmr.R`: UCMR occurrence data

## Running the downloaders
_________________

Download a data set before running its corresponding transformer. To run all the downloaders at once, run `bash run_downloaders.sh` while in the `wsb` directory.

### State WSB downloaders
_________________

The `states` folder contains downloaders for each state with WSB data. WSB data currently exists for 13 states.

[This sheet](https://docs.google.com/spreadsheets/d/1ov0vx0A-qawxLwASHNRUIyXgJXhLjBHIQ4JxdhIyW4o/edit?usp=sharing) lists WSB status and links to existing data for all states.

[TX](https://www3.twdb.texas.gov/apps/waterserviceboundaries): Click Download > Shapefile in the bottom left left corner. Save in the directory `data/boundary/tx` and unzip.

CA: 

AR, AZ, CT, KS, MO, NC, NJ, NM, OK, PA, WA: Download a state's data directly from URL by running `Rscript src/downloaders/states/download_%_wsb.R`, where % is the state's two-letter abbreviation in lowercase. Each downloader calls the functions in the file `download_state_helpers.R` to download data (and unzip if needed).
