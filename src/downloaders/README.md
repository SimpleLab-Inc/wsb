# Overview and contributor guide for downloaders
_________________

_Last updated 2022-03-24_  

This `README` is intended to track and document the sources and relevance of data used in the pipeline.

### List of downloaders
_________________

- `states/download_%_wsb.R`: Water system boundary data for `%` state
- `download_echo.R`: [EPA Enforcement and Compliance History Online Exporter](https://echo.epa.gov/tools/data-downloads#exporter) admin data
- `download_sdwis.py`: [EPA Safe Drinking Water Information System](https://www.epa.gov/enviro/sdwis-model) data
- `download_tigris_ne.R`: [TIGER/Line Shapefiles](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html) from `tigris` package and Natural Earth coastline
- `download_ucmr.R`: [Unregulated Contaminant Monitoring Rule](https://www.epa.gov/dwucmr) occurrence data
- `download_mhp.R`: Mobile home parks point data
- `download_frs.R`: [EPA Facility Registry Services Geospatial](https://www.epa.gov/frs/geospatial-data-download-service) centroids

### Running the downloaders
_________________

Download a data set before running its corresponding transformer. To run all the downloaders at once, run `bash run_downloaders.sh` from the `wsb` directory. Some data must be downloaded manually or retrieved from a state administrator (namely WSB Shapefiles for TX and CA). All data downloads save to a path file specified in your environment variable `WSB_DATA_PATH`.


### State water service boundary downloaders
_________________
 
The `states` folder contains downloaders for each state with readily retrievable service boundary area data. Labeled water service boundaries currently exist for 13 states, but 2 of these states (CA, TX) require a manual download or data request. The `states` folder contains download scripts for the remaining 11 of these states.

- AR, AZ, CT, KS, MO, NC, NJ, NM, OK, PA, WA
  - Download a single state's data directly from URL by running `Rscript src/downloaders/states/download_%_wsb.R`, where % is the state's two-letter abbreviation in lowercase. Each downloader calls the functions in the file `download_state_helpers.R` to download data (and unzip if needed).

- TX
  - Find the Shapefile for Texas [here](https://www3.twdb.texas.gov/apps/waterserviceboundaries). Click Download > Shapefile in the bottom left corner. Save in the directory `data/boundary/tx` and unzip.

- CA
  - Email DDW-PLU@waterboards.ca.gov to request a Shapefile viewable [here](https://gispublic.waterboards.ca.gov/portal/apps/webappviewer/index.html?id=272351aa7db14435989647a86e6d3ad8). Save in the directory `data/boundary/ca` and unzip.

[This sheet](https://docs.google.com/spreadsheets/d/1ov0vx0A-qawxLwASHNRUIyXgJXhLjBHIQ4JxdhIyW4o/edit?usp=sharing) lists whether states have service area data available with relevant links. Upon receiving more information or data for a state's WSB, update this sheet. The links to existing downloadable WSB data are found in the column "Link 2" (or "Link 1").

### ECHO Export downloader
_________________

ECHO is the primary source of facility latitude/longitude data for active community water system facility locations in the pipeline. The downloaded files summarize enforcement, compliance, and attribute data for all environmental facilities registered with EPA.

`src/downloaders/download_echo.R` downloads a zip file with multiple sheets. `ECHO_EXPORTER.CSV` is later filtered and transformed.


### TIGER/Line downloader
_________________

TIGER/Line shapefiles are boundaries for Census Places, or incorporated and census designated places. Where Places are successfully matched to water systems, the Places boundaries are used as a proxy shapefile for the water system service area where no labeled service area boundary exists.

`src/downloaders/download_tigris_ne.R` downloads a Census TIGER/Line shapefiles using the R [tigris](https://rdocumentation.org/packages/tigris/versions/1.6) package, and corrects these places using a natural earth coastline dataset. 


### SDWIS downloader
_________________

SDWIS data provide a relevant data on community water systems nationwide. The downloader outputs `WATER_SYSTEM.CSV`, `WATER_SYSTEM_FACILITY.CSV`, `GEOGRAPHIC_AREA.CSV`, and `SERVICE_AREA.CSV`. Ultimately, `WATER_SYSTEM.CSV` serves as the master list for water systems, while `GEOGRAPHIC_AREA.CSV` and `SERVICE_AREA.CSV` provide supplementary geographic information and relevant features for modeling.

`src/downloaders/download_sdwis.py` downloads all files, using the [aria2](https://aria2.github.io/) package, which is a multi sources/multiprotocol download utility. SDWIS limits queries to 10K rows per query, and `download_helpers.py` supports the downloader with functions to write queries to a text file which get read by the downloader.


### UCMR downloader
_________________

UCMR maintains contaminant occurrence data for water systems required by EPA to monitor specific unregulated contaminants. The most recent two UCMR periods (UCMR3 and UCMR4) collected information about zipcodes served for each water system participating in UCMR. This pipeline uses `UCMR4_ZipCodes.txt` and `UCMR3_ZipCodes.txt` and zipcode shapefiles from [tigris](https://rdocumentation.org/packages/tigris/versions/1.6) to assign zipcode served centroids to water systems, where available.

`src/downloaders/download_ucmr.R` downloads all files from UCMR3 and UCMR4.


### MHP downloader
_________________

Mobile home park location data is available as centroids (longitude/latitude) from the Homeland Infrastructure Foundation Level Data (HIFLD) [database](https://hifld-geoplatform.opendata.arcgis.com/datasets/mobile-home-parks/explore?location=42.190493%2C66.088063%2C3.53). Where no labeled water system boundary data exists, the mobile home park centroid may be a preferrable centroid to the ECHO centroids for modeling approximate service areas.

`src/downloaders/download_mhp.R` downloads mobile home park centroids.


### FRS downloader
_________________

[FRS](https://www.epa.gov/frs) maintains and organizes all environmental facilities registered with EPA. In particular, FRS creates the facility location data that ECHO uses as a primary data source for water system facility location data. The FRS dataset is *not used* in the pipeline, but a downloader exists to check for updates and compare with ECHO output data.

`src/downloaders/download_frs.R` downloads facility centroid data.


