# Download MO water service boundaries ------------------------------------

setwd("src/downloaders/states/")
source("download_state_helpers.R")

# Data Source: Missouri ArcGIS geojson water system boundary
url <- paste0("https://opendata.arcgis.com/datasets/",
              "c3bee75a86e04856b28d7f1ce2a24e6f_0.geojson")

download_wsb(url, "mo")
