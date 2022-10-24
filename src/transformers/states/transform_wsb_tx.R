# transform TX water system data to standard model -------------------

cat("Preparing to transform TX polygon boundary data.\n\n")

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

# Read layer for TX water service boundaries, clean, transform CRS
tx_wsb <- st_read(path(data_path, 
                       "boundary/tx/PWS_shapefile/PWS_Export.shp")) %>% 
  # clean whitespace
  f_clean_whitespace_nas() %>%
  # transform to area weighted CRS
  st_transform(epsg_aw) %>%
  # correct invalid geometries
  st_make_valid()

cat("Read TX boundary layer; cleaned whitespace; corrected geometries.\n ")

# Compute centroids, convex hulls, and radius assuming circular
tx_wsb <- tx_wsb %>%
  bind_rows() %>%
  mutate(
    state          = "TX",
    # importantly, area calculations occur in area weighted epsg
    st_areashape   = st_area(geometry),
    convex_hull    = st_geometry(st_convex_hull(geometry)),
    area_hull      = st_area(convex_hull),
    radius         = sqrt(area_hull/pi)
  ) %>%
  # transform back to standard epsg
  st_transform(epsg) %>%
  # compute centroids
  mutate(
    centroid       = st_geometry(st_centroid(geometry)),
    centroid_long  = st_coordinates(centroid)[, 1],
    centroid_lat   = st_coordinates(centroid)[, 2],
  ) %>%
  # select columns and rename for staging
  select(
    # data source columns
    pwsid          = PWSId,
    pws_name       = pwsName,
    state,
    #    county,
    #    city,
    #    owner,
    # geospatial columns
    st_areashape,
    centroid_long,
    centroid_lat,
    radius,
    geometry
  )
cat("Computed area, centroids, and radii from convex hulls.\n")
cat("Combined into one layer; added geospatial columns.\n")


# delete layer if it exists, then write to geopackage
path_out <- path(staging_path, "wsb_labeled_tx.gpkg")
if(file_exists(path_out)) file_delete(path_out)

st_write(tx_wsb, path_out)
cat("Wrote clean, labeled data to file.\n\n\n")
