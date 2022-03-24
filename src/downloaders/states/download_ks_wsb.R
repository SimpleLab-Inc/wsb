# Download KS water system data -------------------------------------------

setwd("src/downloaders/states/")
source("download_state_helpers.R")

# Data Source: Kansas ArcGIS shapefile water system boundary
url <- paste0("https://data.kansasgis.org/catalog/",
              "administrative_boundaries/shp/pws/PWS_bnd_2021_0430.zip")

download_wsb(url, "ks")
