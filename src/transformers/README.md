# Overview and contributor guide for transformers
_________________

_Last updated 2022-03-24_  

This `README` is intended to track and document the scripts that transform data.

### List of transformers
_________________

- `states/transform_%_wsb.R`: Water system boundary data for `%` state
- `transform_echo.R`: EPA Enforcement and Compliance History Online Exporter admin data
- `transform_sdwis.py`: EPA Safe Drinking Water Information System data
- `transform_tigris_ne.R`: TIGER/Line Shapefiles from `tigris` package and Natural Earth coastline
- `transform_ucmr.R`: Unregulated Contaminant Monitoring Rule occurrence data
- `transform_mhp.R`: Mobile home parks point data
- `transform_frs.R`: EPA Facility Registry Services Geospatial centroids


### Running the transformers
_________________

After downloading a dataset, its corresponding transformer must be run to clean the data. To run all transformers at once, run `bash run_transformers.sh` from the `wsb` directory. All transformed data save to a path file specified in the environment variable `WSB_STAGING_PATH`.


### State water service boundary transformers
_________________

Each state WSB transformer includes the basic steps of cleaning excess whitespace, generating geospatial information, and creating a standard schema. The output of each state WSB transformer is a geojson file in a folder labeled with the two-letter state abbreviation in lowercase, and the folder is in the staging directory specified by the environment variable `WSB_STAGING_PATH`. This geojson filename has the format `%_wsb_labeled.geojson`, where % is the state's two-letter abbreviation in lowercase. 

#### Schema

| Column name | Data type |
| ----------- | ----------- |
| pwsid      | character  |
| pws_name   | character |
| state   | character |
| county   | character |
| city   | character |
| source   | character |
| owner   | character |
| st_areashape   | numeric  |
| centroid_long   | numeric  |
| centroid_lat   | numeric  |
| radius   | numeric  |
| geometry   | sfc_multipolygon  |

#### Geospatial transformations 

The geometry column is transformed to an area weighted CRS, which is set in the environment variable `WSB_EPSG_AW`, before performing area calculations generating the columns st_areashape and radius. The data is then transformed to the standard CRS, which is set in the environment variable `WSB_EPSG`. Finally, centroid_long and centroid_lat are computed.

#### Data source transformations

Each state transformer cleans excess whitespace, assigns a state column, and selects data that fits in the standard schema. Selected columns are those matching pwsid and pws_name, as well as the county, city, source, and owner of the water system, if available. The columns source and owner may be removed in a future refactor.

If a state's pwsid is not in the standard format, that pwsid is reformatted. This includes operations like adding the state abbreviation (and a state code if necessary; see WA) to the front of the pwsid or removing invalid pwsid's. Invalid pwsid's are filtered out for the states MO, NM, and WA.




