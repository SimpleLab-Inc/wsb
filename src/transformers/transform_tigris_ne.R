# transform TIGRIS places and crop to oceans polyline ---------------------

library(fs)
library(sf)
library(tidyverse)
library(tigris)
library(rmapshaper)


# path to save raw data, staging data, and standard projection
data_path    <- Sys.getenv("WSB_DATA_PATH")
staging_path <- Sys.getenv("WSB_STAGING_PATH")
epsg         <- Sys.getenv("WSB_EPSG")

# download large files without timeout error
options(timeout = 100000)

# read Natural Earth ocean geometry
ocean <- st_read(path(data_path, "ne/ocean/ne-ocean-10m/ne_10m_ocean.shp")) %>% 
  select(geometry)

# transform places to ocean crs, make valid, intersect with oceans, 
# reproject to projected crs, and write
places <- read_rds(path(data_path, "tigris/tigris_places.rds"))
places_clean <- places %>% 
  st_transform(st_crs(ocean)$epsg) %>% 
  st_make_valid() %>%
  st_intersection(st_make_valid(ocean)) %>% 
  st_transform(epsg) %>% 
  st_make_valid()

# sanity check that oceans are removed
# mapview::mapview(places_clean)

# write clean TIGRIS places
path_out <- path(staging_path, "tigris_places_clean.geojson")
if(file_exists(path_out)) file_delete(path_out)

st_write(places_clean, path_out)
cat("Wrote clean TIGRIS places.\n")
