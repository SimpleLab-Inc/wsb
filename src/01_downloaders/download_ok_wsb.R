# Download OK water system data

library(tidyverse)
library(here)

# Allow for longer timeout to map download file
options(timeout = 10000)

# Data Source: Oklahoma ArcGIS geojson water system boundary
ok_url <- paste0("https://opendata.arcgis.com/datasets/",
                 "d015bc14d3b84b8985ff3a4fd55c0844_0.geojson")

# create dir to store file and download
fs::dir_create(here("data/boundary/ok"))
download.file(ok_url, here("data/boundary/ok/ok.geojson"))
cat("Downloaded OK data.\n")
