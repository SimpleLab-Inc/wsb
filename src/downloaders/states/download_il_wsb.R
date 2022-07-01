# Download IL water system data -------------------------------------------

source(here::here("src/downloaders/states/download_state_helpers.R"))

# Data Source: IL Geospatial Data Clearinghouse 
url <- paste0("https://clearinghouse.isgs.illinois.edu/sites/clearinghouse.isgs/files/Clearinghouse/data/ISWS/Hydrology/zips/",
              "Illinois_Municipal_Water_Use_2012.zip")

download_wsb(url, "il")

