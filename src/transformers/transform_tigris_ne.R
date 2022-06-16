# transform TIGRIS places and crop to oceans polyline ---------------------

library(fs)
library(sf)
library(tidyverse)
library(tigris)
library(rmapshaper)


# path to save raw data, staging data, and standard projection
data_path    <- Sys.getenv("WSB_DATA_PATH")
staging_path <- Sys.getenv("WSB_STAGING_PATH")
epsg         <- as.numeric(Sys.getenv("WSB_EPSG"))

# download large files without timeout error
options(timeout = 100000)

# read Natural Earth ocean geometry
ocean <- st_read(path(data_path, "ne/ocean/ne-ocean-10m/ne_10m_ocean.shp")) %>% 
  select(geometry) %>% 
  st_make_valid()

# transform places to ocean crs, make valid
places <- read_rds(path(data_path, "tigris/tigris_places.rds")) %>% 
  st_transform(st_crs(ocean)$epsg) %>% 
  st_make_valid() 

# intersect places with oceans and write
places_clean <- places %>% 
  st_intersection(ocean) %>% 
  st_make_valid() %>% 
  janitor::clean_names() 

# sanity check that oceans are removed
# mapview::mapview(places_clean)

# download tigris population data
pop <- read_csv(path(data_path, "tigris/tigris_pop.csv")) %>%
  select(geoid, population)

# join population data to places_clean
places_clean <- places_clean %>%
  left_join(pop, by = "geoid")

# write clean TIGRIS places
path_out <- path(staging_path, "tigris_places_clean.geojson")
if(file_exists(path_out)) file_delete(path_out)

st_write(places_clean, path_out)
cat("Wrote clean TIGRIS places.\n")
