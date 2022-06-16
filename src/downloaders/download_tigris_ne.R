# download TIGRIS places and Natural Earth (ne) coastline -----------------

library(fs)
library(sf)
library(tigris)
library(rmapshaper)
library(readr)
library(tidyverse)
library(tidycensus)


# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")
census_api_key <- Sys.getenv("CENSUS_API_KEY")

# Tell tidycensus our key (don't forget to activate it first!)
census_api_key(census_api_key)

# download large files without timeout error
options(timeout = 100000, tigris_use_cache = TRUE)
states_list <- c(state.abb, "DC")

# create dirs
dir_create(path(data_path, "tigris"))
dir_create(path(data_path, "ne/ocean"))

# download all TIGRIS places, simplify polygons, save
places <- tigris::places(states_list)

places <- places %>% 
  rmapshaper::ms_simplify(
    keep_shapes = TRUE,
    # https://github.com/ateucher/rmapshaper/issues/83
    # and https://github.com/ateucher/rmapshaper#using-the-system-mapshaper or 
    # https://docs.npmjs.com/resolving-eacces-permissions-errors-when-installing-packages-globally
    sys = TRUE)

write_rds(places, path(data_path, "tigris/tigris_places.rds"))
cat("Downloaded and wrote TIGRIS places.\n")

# download and write population data for TIGRIS places
pop <- get_decennial(
    geography = "place",     # census-designated places
    state = states_list,
    year = 2020,
    variables = "P1_001N",   # selects population data for 2020
    geometry = FALSE,
    cb = FALSE
  ) %>%
  select(
    geoid        = GEOID,
    name         = NAME,
    population   = value
  ) %>%
  write_csv(., path(data_path, "tigris/tigris_pop.csv"))

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
