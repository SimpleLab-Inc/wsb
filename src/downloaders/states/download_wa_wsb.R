# Download WA water system data -------------------------------------------

setwd("src/downloaders/states/")
source("download_state_helpers.R")

# Data Source: Washington ArcGIS Geodatabase water system boundary
url <- paste0("https://opendata.arcgis.com/datasets/",
              "b09475f47a5a46ca90fe6a168fb22e6d_0.geojson")

download_wsb(url, "wa")
