# transform NJ water system data to standard model -------------------

cat("Starting transformation for NJ.\n\n")

library(fs)
library(sf)
library(tidyverse)

# helper function
source(here::here("src/functions/f_clean_whitespace_nas.R"))

# path to save raw data, staging data, and standard projection
data_path    <- Sys.getenv("WSB_DATA_PATH")
staging_path <- Sys.getenv("WSB_STAGING_PATH")
epsg         <- as.numeric(Sys.getenv("WSB_EPSG"))
epsg_aw      <- Sys.getenv("WSB_EPSG_AW")

# Read layer for NJ water service boundaries, clean, transform CRS
nj_wsb <- st_read(dsn = path(data_path, "boundary/nj/nj.geojson")) %>% 
  # clean whitespace
  f_clean_whitespace_nas() %>%
  # transform to area weighted CRS
  st_transform(epsg_aw) %>%
  # correct invalid geometries
  st_make_valid()

cat("Read NJ boundary layer; cleaned whitespace; corrected geometries.\n ")

# Compute centroids, convex hulls, and radius assuming circular
nj_wsb <- nj_wsb %>%
  bind_rows() %>%
  mutate(
    state          = "NJ",
    # importantly, area calculations occur in area weighted epsg
    st_areashape   = st_area(geometry),
    convex_hull    = st_geometry(st_convex_hull(geometry)),
    area_hull      = st_area(convex_hull),
    radius         = sqrt(area_hull/pi)
  ) %>%
  # transform back to standard epsg for geojson write
  st_transform(epsg) %>%
  mutate(
    centroid       = st_geometry(st_centroid(geometry)),
    centroid_long  = st_coordinates(centroid)[, 1],
    centroid_lat   = st_coordinates(centroid)[, 2],
  ) %>%
  # select columns and rename for staging
  select(
    # data source columns
    pwsid          = PWID,
    pws_name       = SYS_NAME,
    state,
    #    county,   # county code is first 2 digits of PWID
    #    city,
    #    source,
    #    owner,
    # geospatial columns
    st_areashape,
    centroid_long,
    centroid_lat,
    area_hull,
    radius,
    geometry
  )
cat("Computed area, centroids, and radii from convex hulls.\n")
cat("Combined into one layer; added geospatial columns.\n")

# create state dir in staging
dir_create(path(staging_path, "nj"))

# delete layer if it exists, then write to geojson
path_out <- path(staging_path, "nj/nj_wsb_labeled.geojson")
if(file_exists(path_out)) file_delete(path_out)

st_write(nj_wsb, path_out)
cat("Wrote clean, labeled data to geojson.\n\n\n") 
