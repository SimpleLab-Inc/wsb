# Transform OK water service areas ----------------------------------------

library(fs)
library(sf)
library(tidyverse)
library(tigris)
library(rmapshaper)

# helper function
source(here::here("src/functions/f_clean_whitespace_nas.R"))

# path to save raw data, staging data, and standard projection
data_path    <- Sys.getenv("WSB_DATA_PATH")
staging_path <- Sys.getenv("WSB_STAGING_PATH")
epsg         <- Sys.getenv("WSB_EPSG")

# Read layer for OK water service boundaries, clean names, transform to standard epsg
ok_sp <- st_read(dsn = path(data_path, "boundary/ok/ok.geojson")) %>% 
  janitor::clean_names() %>% 
  st_transform(epsg) %>%
  f_clean_whitespace_nas() %>%
  # Correct invalid geometries
  st_make_valid()

cat("Read OK boundary layer, cleaned names, transformed to CRS:", epsg, "\n ")
cat("Fixed invalid geometries.")


# Compute centroids, convex hulls, and radius assuming circular -----------
ok_sp <- ok_sp %>%
   mutate(
    centroid    = st_geometry(st_centroid(geometry)),
    convex_hull = st_geometry(st_convex_hull(geometry)),
    area_hull   = st_area(convex_hull),
    radius      = sqrt(area_hull/pi)
  )
# 
# # sanity checks
# ok_sp$convex_hull %>% plot(col = 'lightblue')
# ok_sp$geometry %>% plot(col = "green", add = TRUE)
# ok_sp$centroid %>% plot(col = 'red', pch = 3, add = TRUE)

# Save transformed OK data to staging -------------------------------------
path_out <- path(staging_path, "ok_wsb.geojson")
if(file_exists(path_out)) file_delete(path_out)

st_write(ok_sp, path_out)

cat("Wrote clean OK boundaries to staging.\n")