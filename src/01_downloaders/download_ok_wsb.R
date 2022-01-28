# Download water system data

# Setup  -----------------------------------------------------------------------

library(tidyverse)
library(here)
library(fs)
library(glue)


# Allow for longer timeout to map download file
options(timeout = 10000)

# Download ---------------------------------------------------------------------
# Data Source: Oklahoma ArcGIS
## 1 geojson water system boundary from ArcGIS API
ok_url <- "https://opendata.arcgis.com/datasets/d015bc14d3b84b8985ff3a4fd55c0844_0.geojson"

map2(ok_url, "ok",
     ~download.file(.x, here("data/boundary", .y, glue("{.y}.geojson"))))