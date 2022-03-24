# Download PA water system data -------------------------------------------

setwd("src/downloaders/states/")
source("download_state_helpers.R")

# Data Source: Pennsylvania ArcGIS geojson water system boundary
url <- paste0("https://www.pasda.psu.edu/json/PublicWaterSupply2022_01.geojson")

download_wsb(url, "pa")
