# Download AZ water system data -------------------------------------------

setwd("src/downloaders/states/")
source("download_state_helpers.R")

# Data Source: Arizona ArcGIS geojson water system boundary
url <- paste0("https://opendata.arcgis.com/datasets/",
              "9992e59e46bb466584f9694f897f350a_0.geojson")

download_wsb(url, "az")
