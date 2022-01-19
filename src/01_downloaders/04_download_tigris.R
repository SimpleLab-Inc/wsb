# download TIGRIS places, crop to oceans for coastal polygons that
# jut into the water bodies, and save

library(tidyverse)
library(sf)
library(here)
library(tigris)
library(rmapshaper)
library(glue)

# download large files without timeout error
options(timeout = 100000)

# standard proj
epsg <- 3310

# create dirs
fs::dir_create(here("data/tigris"))
fs::dir_create(here("data/ne/ocean"))

# download all TIGRIS places, simplify polygons, save
places <- state.abb %>% 
  tigris::places() %>% 
  rmapshaper::ms_simplify(keep_shapes = TRUE) 

places %>% 
  write_rds(here("data/tigris/places.rds"))
# places <- read_rds(here("data/tigris/places.rds"))

# download and unzip Natural Earth oceans polygons to 
# remove water bodies from TIGRIS places
url_ne <- paste0("https://www.naturalearthdata.com/",
                 "http//www.naturalearthdata.com/",
                 "download/10m/physical/ne_10m_ocean.zip")
download.file(url_ne, 
              destfile = here(glue("data/ne/ocean/ocean.zip")))

unzip(zipfile = here(glue("data/ne/ocean/ocean.zip")),
      exdir   = here(glue("data/ne/ocean/ne-ocean-10m")))

# read in ocean geometry
ocean <- st_read(here("data/ne/ocean/ne-ocean-10m/ne_10m_ocean.shp")) %>% 
  select(geometry)

# transform places to ocean crs, make valid, intersect with oceans, 
# reproject to projected crs, and write
places <- places %>% 
  st_transform(st_crs(ocean)$epsg) %>% 
  st_make_valid() %>%
  st_intersection(st_make_valid(ocean)) %>% 
  st_transform(epsg) %>% 
  st_make_valid()

# sanity check that oceans are removed
mapview::mapview(places)

# write places
places %>% 
  write_rds(here("data/tigris/places_clean.rds"))
