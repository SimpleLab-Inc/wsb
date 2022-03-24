# Download OK water system data -------------------------------------------

source(here::here("src/downloaders/states/download_state_helpers.R"))

# Data Source: Oklahoma ArcGIS geojson water system boundary
url <- paste0("https://opendata.arcgis.com/datasets/",
              "d015bc14d3b84b8985ff3a4fd55c0844_0.geojson")

download_wsb(url, "ok")
