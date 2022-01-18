library(tidyverse)
library(sf)
library(here)
library(tigris)
library(rmapshaper)
library(glue)

# download large files without timeout error
options(timeout = 100000)

epsg <- 3310

# download all TIGRIS places and simplify polygons
places <- state.abb %>% 
  tigris::places() %>% 
  rmapshaper::ms_simplify(keep_shapes = TRUE) 

# download and unzip Natrual Earth oceans + lakes polygons to 
# remove water bodies from TIGRIS places
url_ne <- paste0("https://www.naturalearthdata.com/",
                 "http//www.naturalearthdata.com/",
                 "download/10m/physical/ne_10m")
ne_layers <- c("ocean", "lakes")

walk(ne_layers,
     ~download.file(
       glue("{url_ne}_{.x}.zip"), 
       destfile = here(glue("data/ne/{.x}/{.x}.zip"))))

walk(ne_layers,
     ~unzip(zipfile = here(glue("data/ne/{.x}/{.x}.zip")),
            exdir   = here(glue("data/ne/{.x}/ne-{.x}-10m"))))

ocean <- st_read(here("data/ne/ocean/ne-ocean-10m/ne_10m_ocean.shp"))
lakes <- st_read(here("data/ne/lakes/ne-lakes-10m/ne_10m_lakes.shp")) %>% 
  ms_simplify(keep_shapes = TRUE)

# combine oceans and lakes
ocean_lakes <- bind_rows(ocean, lakes) %>% st_make_valid()

# transform places to ocean crs, make valid, intersect with oceans, 
# reproject to projected crs, and write
places <- places %>% 
  st_transform(st_crs(ocean_lakes)$epsg) %>% 
  st_make_valid() %>%  
  st_intersection(ocean_lakes) %>% 
  st_transform(epsg)

# sanity check that oceans and lakes are removed
mapview::mapview(places)

# write places
places %>% 
  write_rds(here("data/tigris/places.rds"))
