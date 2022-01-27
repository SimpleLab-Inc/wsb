# transform labeled water system data to standard model

library(tidyverse)
library(here)
library(fs)
library(sf)

# projected metric coordinate reference system for calculations
epsg <- 3310

# read labeled data, simplify polygons, transform to 3310, and make valid
f <- dir_ls(here("data/boundary"), recurse = TRUE, glob = "*geojson")
d <- map(f, ~st_read(.x) %>% 
           rmapshaper::ms_simplify(keep_shapes = TRUE) %>% 
           st_transform(epsg) %>% 
           st_make_valid())

# validate equal CRS
map_int(d, ~st_crs(.x)$epsg) %>% unique()

# compute centroids
d %>% 
  mutate(centroid = st_centroid(geometry))

# compute convex hull and circular area

# write convex hull for sanity checks



