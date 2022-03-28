# download TIGRIS places and Natural Earth (ne) coastline -----------------

library(fs)
library(sf)
library(tigris)
library(rmapshaper)
library(readr)
library(tidyverse)

# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# download large files without timeout error
options(timeout = 100000)

# create dirs
dir_create(path(data_path, "tigris"))
dir_create(path(data_path, "ne/ocean"))

# download all TIGRIS places, simplify polygons, save
fips_ids <- fips_codes %>% 
  filter(state %in% c(state.abb, "DC")) %>% 
  pull(state_code) %>% 
  unique()

places <- state.abb %>% 
  tigris::places(fips_ids)

places <- places %>% 
  rmapshaper::ms_simplify(
    keep_shapes = TRUE,
    # https://github.com/ateucher/rmapshaper/issues/83
    # and https://github.com/ateucher/rmapshaper#using-the-system-mapshaper
    sys = TRUE)

write_rds(places, path(data_path, "tigris/tigris_places.rds"))
cat("Downloaded and wrote TIGRIS places.\n")

# download and unzip Natural Earth oceans polygons, used to 
# remove water bodies from TIGRIS places in the transformer
url_ne <- paste0("https://www.naturalearthdata.com/",
                 "http//www.naturalearthdata.com/",
                 "download/10m/physical/ne_10m_ocean.zip")
download.file(url_ne, 
              destfile = path(data_path, "ne/ocean/ocean.zip"))

unzip(zipfile = path(data_path, "ne/ocean/ocean.zip"),
      exdir   = path(data_path, "ne/ocean/ne-ocean-10m"))
cat("Downloaded and wrote Natural Earth Oceans.\n")
