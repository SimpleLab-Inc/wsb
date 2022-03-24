# Download PA water system data -------------------------------------------

source(here::here("src/downloaders/states/download_state_helpers.R"))

# Data Source: Pennsylvania ArcGIS geojson water system boundary
url <- "https://www.pasda.psu.edu/json/PublicWaterSupply2022_01.geojson"

download_wsb(url, "pa")
