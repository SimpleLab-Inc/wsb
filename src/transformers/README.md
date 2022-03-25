# Overview and contributor guide for transformers
_________________

_Last updated 2022-03-24_  

This `README` is intended to track and document the scripts that transform data.

### List of transformers
_________________

- `states/transform_%_wsb.R`: Water system boundary data for `%` state
- `transform_echo.R`: EPA Enforcement and Compliance History Online Exporter admin data
- `transform_sdwis_%.py`: EPA Safe Drinking Water Information System data for `%` SDWIS table
- `transform_tigris_ne.R`: TIGER/Line Shapefiles from `tigris` package and Natural Earth coastline
- `transform_ucmr.R`: Unregulated Contaminant Monitoring Rule occurrence data
- `transform_mhp.R`: Mobile home parks point data
- `transform_frs.R`: EPA Facility Registry Services Geospatial centroids


### Running the transformers
_________________

After downloading a dataset, its corresponding transformer must be run to clean the data. To run all transformers at once, run `bash run_transformers.sh` from the `wsb` directory. All transformed data save to a path file specified in the environment variable `WSB_STAGING_PATH`.


### State water service boundary transformers
_________________

Each state water system boundary transformer includes basic steps of cleaning excess white space, generating geospatial information about the area and radius of a service area, and creating a standard schema. The output of each state WSB transformer is a geojson file in a folder labeled with the two-letter state abbreviation in lowercase, and the folder is in the staging directory specified by the environment variable `WSB_STAGING_PATH`. This geojson filename has the format `%_wsb_labeled.geojson`, where % is the state's two-letter abbreviation in lowercase. 

#### Schema

| Column name | Data type | Description |
|----------- | ----------- | ----------- |
| pwsid      | character  | public water system identifier |
| pws_name   | character | public water system name |
| state   | character | state location of water system service area |
| county   | character | county location of water system service area |
| city   | character | city location of water system service area |
| owner   | character | ownership of water system |
| st_areashape   | numeric  | area of water system (square meters) |
| centroid_long   | numeric  | longitude of water system centroid |
| centroid_lat   | numeric  | latitude of water system centroid |
| radius   | numeric  | radius of water system convex hull (meters) |
| geometry   | sfc_multipolygon  | polygon geometry of water service area |

#### Geospatial transformations 

The geometry column is transformed to a CRS optimal for area calculations before generating the columns `st_areashape` and `radius`. We currently use [Albers Equal Area Conic projected CRS](https://epsg.io/102003) for equal area calculations. For AK and HI, we need to shift geometry into this CRS so area calculations are minimally distorted (see `tigris::shift_geometry(d, preserve_area = TRUE)` at [this webpage](https://walker-data.com/census-r/census-geographic-data-and-applications-in-r.html#shifting-and-rescaling-geometry-for-national-us-mapping)). The data is then transformed to the standard CRS, which is set in the environment variable `WSB_EPSG`. `WSB_EPSG` is a World Geodetic System 1984 (see [here](https://epsg.io/4326)) which is the CRS that geojson stores. Finally, in the same CRS as the service area geometry, centroid_long and centroid_lat are computed.

#### Data source transformations

Each state transformer cleans excess white space, assigns a state column, and selects data that fits in the standard schema. Selected columns are those matching `pwsid` and `pws_name`, as well as the `county`, `city`, `source`, and `owner` of the water system, if available. The column `owner` may be removed in a future refactor due to the fact that it is rarely populated and its data are easily retrievable from other data sources.

If a `pwsid` is not in the standard format, that `pwsid` is reformatted. This includes operations like adding the state abbreviation (and a state code if necessary; see [WA](https://github.com/SimpleLab-Inc/wsb/blob/develop/src/transformers/states/transform_wsb_wa.R) to the front of the `pwsid` or removing invalid `pwsids`. Invalid `pwsids` are filtered out for the states MO, NM, and WA.

### ECHO Export transformer
_________________

The ECHO transformer run with `src/transformers/transform_echo.R` includes basic steps of cleaning excess white space, filtering to relevant columns and rows for water systems, and some geospatial processing. The geospatial processing on the ECHO data largely focuses on rendering latitude and longitude values into point geometries and dropping water system facility locations (centroids) that are not in the state served by the water system using [f_drop_imposters()](https://github.com/SimpleLab-Inc/wsb/blob/develop/src/functions/f_drop_imposters.R).

The output of the ECHO transformer is a cleaned geojson of water system facilities nationwide.


### TIGER/Line transformer
_________________

TIGER/Line shapefiles are boundaries for Census Places, or incorporated and census designated places. Because these boundaries overlap with ocean areas in some cases,  `src/transformers/transform_tigris_ne.R` intersects Census Places with Natural Earth ocean geometry to remove ocean areas from Census places.

The output of the TIGER/Line transformer is a cleaned geojson of TIGER/Line shapefiles without ocean overlap.


### SDWIS transformers
_________________

SDWIS data provide a relevant data on community water systems nationwide. There are four transformer scripts:

-`src/transformer/transform_sdwis_ws.py`: Transforms the water system table
-`src/transformer/transform_sdwis_wsf.py`: Transforms the water system facilities table
-`src/transformer/transform_sdwis_geo_areas.py`: Transforms the geographic area table
-`src/transformer/transform_sdwis_service.py`: Transforms the service area table

Each transformer includes basic steps of cleaning white space, sanitizing booleans, standardizing dates, and removing duplicate entries. The output is a clean `sdwis_%_.csv` file where `%` is the appropriate table name. `sdwis_water_system.csv` serves as the master file for water system identifiers and names.

### UCMR transformer
_________________

UCMR includes information about zipcodes served for each water system participating in UCMR. The UCMR transformer, `src/transformer/transform_ucmr.R`, includes basic cleaning steps of cleaning white space and removing invalid zip codes. The transformer combines zipcode information across two phases of UCMR (UCMR3 and UCMR4) for maximal data coverage. Finally, zipcode areas from the Census are joined to water systems and similar geoprocessing to the labeled water service boundary transformers is conducted: convex hull area, radius, and centroids are calculated.

The UCMR transformer output is a cleaned geojson file linking `pwsid` with zipcodes served and the zipcode centroids.


### MHP transformer
_________________

The mobile home park transformer run with `src/transformers/transform_mhp.R` includes basic steps of cleaning excess white space, standardizing colum names, and some geospatial processing. The geospatial processing on the MHP data largely focuses on rendering latitude and longitude values into point geometries and dropping locations (centroids) that are not in the same state of the MHP [f_drop_imposters()](https://github.com/SimpleLab-Inc/wsb/blob/develop/src/functions/f_drop_imposters.R).

The output of the MHP transformer is a cleaned geojson of mobile home park locations nationwide.


### FRS transformer
_________________

The FRS transformer run with `src/transformers/transform_frs.R` includes basic steps of cleaning excess white space, filtering to relevant columns for active, community water systems, and some geospatial processing. The geospatial processing on the FRS data largely focuses on rendering latitude and longitude values into point geometries and dropping water system facility locations (centroids) that are not in the state served by the water system using [f_drop_imposters()](https://github.com/SimpleLab-Inc/wsb/blob/develop/src/functions/f_drop_imposters.R).

The FRS dataset is *not used* in the pipeline, but a transformer exists to check for updates and compare with ECHO output data.




