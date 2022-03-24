# Download AR water system data -------------------------------------------

source(here::here("src/downloaders/states/download_state_helpers.R"))

# Data Source: Arkansas ArcGIS shapefile water system boundary
url <- paste0("https://geostor-vectors.s3.amazonaws.com/Utilities/SHP/",
              "PUBLIC_WATER_SYSTEMS.zip")

download_wsb(url, "ar")
