# Download NJ water system data -------------------------------------------

setwd("src/downloaders/states/")
source("download_state_helpers.R")

# Data Source: New Jersey ArcGIS geojson water system boundary
url <- paste0("https://opendata.arcgis.com/datasets/",
              "00e7ff046ddb4302abe7b49b2ddee07e_13.geojson")

download_wsb(url, "nj")
