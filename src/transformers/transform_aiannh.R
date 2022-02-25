# American Indian/Alaska Native/Native Hawaiian (AIANNH) Areas 
# https://www2.census.gov/geo/pdfs/maps-data/data/tiger/tgrshp2019/TGRSHP2019_TechDoc_Ch3.pdf

library(fs)
library(sf)
library(tidyverse)
library(tigris)

# tell tigris to cache Census shapefile downloads for faster subsequent runs
# download large files without timeout error
options(tigris_use_cache = TRUE, timeout = 100000)

# path to save raw data, staging data, and standard projection
data_path    <- Sys.getenv("WSB_DATA_PATH")
staging_path <- Sys.getenv("WSB_STAGING_PATH")
epsg         <- as.numeric(Sys.getenv("WSB_EPSG"))

# read Natural Earth ocean geometry (downloaded with tigris places downloader)
ocean <- st_read(path(data_path, "ne/ocean/ne-ocean-10m/ne_10m_ocean.shp")) %>%
  select(geometry)

# transform aiannh areas to ocean crs, make valid, intersect with oceans, 
# reproject to projected crs, and write
aiannh <- tigris::native_areas() %>%
  rmapshaper::ms_simplify(
    keep_shapes = TRUE,
    # https://github.com/ateucher/rmapshaper/issues/83
    # and https://github.com/ateucher/rmapshaper#using-the-system-mapshaper
    sys = TRUE
  ) %>%
  st_transform(st_crs(ocean)$epsg) %>% 
  st_make_valid() %>%
  st_intersection(st_make_valid(ocean)) %>% 
  st_transform(epsg) %>% 
  st_make_valid()

# write clean AIANNH places
path_out <- path(staging_path, "aiannh/aiannh_places.geojson")
if(file_exists(path_out)) file_delete(path_out)

st_write(places_clean, path_out)
cat("Wrote clean AIANNH places.\n")
