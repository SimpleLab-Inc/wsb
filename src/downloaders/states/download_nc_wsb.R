# Download NC water service boundaries ------------------------------------

setwd("src/downloaders/states/")
source("download_state_helpers.R")

# Data Source: North Carolina ArcGIS geojson water system boundary
url <- paste0("https://opendata.arcgis.com/datasets/",
              "58548b90bdfd4148829103ac7f4db9ce_4.geojson")

download_wsb(url, "nc")
