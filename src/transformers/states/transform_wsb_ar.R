# transform MA water system data to standard model -------------------

cat("Preparing to transform MA polygon boundary data.\n\n")

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

# Lookup for AR pwisds where name does not automatically match to shapefile
pwsid_supp <- read_csv("crosswalks/ar_pwsid_lookup.csv")

# Read layer for MA water service boundaries, clean, transform CRS
ar_wsb <- st_read(path(data_path, "boundary/ar/PUBLIC_WATER_SYSTEMS.shp")) %>% 
  # clean whitespace
  f_clean_whitespace_nas() %>%
  # transform to area weighted CRS
  st_transform(epsg_aw) %>%
  # correct invalid geometries
  st_make_valid() %>%
  janitor::clean_names()

cat("Read AR boundary layer; cleaned whitespace; corrected geometries.\n ")

# Match water system names to sdwis to get pwsid
# Note that comparing to this csv requires having downloaded and cleaned the SDWIS data
# TODO: identify best strategy for this

# Get active cws in AR
ar_sdwis <- read_csv(path(staging_path, "sdwis_water_system.csv")) %>%
  filter(primacy_agency_code == "AR",
         pws_activity_code == "A")

# Select names and object ids from spatial dataset
ar_names <- ar_wsb %>% select(objectid, pws_name) %>%
  st_drop_geometry()

# Join spatial dataset system names with sdwis 
ar_pwsids <- ar_names %>% left_join(ar_sdwis, by = c("pws_name")) %>%
  select(objectid, pws_name, pwsid)

# Pull out the number of missing ids
# From this list, pwsids were manually assigned to create the lookup
na_pwsids <- ar_pwsids %>% filter(is.na(pwsid)) %>%
  left_join(pwsid_supp, by = c("pws_name")) %>%
  select(objectid, pws_name, pwsid.y) %>%
  rename(pwsid = pwsid.y)

# Concatenate pwsid dataframes
ar_pwsids <- ar_pwsids %>% 
  rbind(na_pwsids) %>%
  distinct() %>%
  filter(!is.na(pwsid))

# Rejoin pwsid with shapefiles
ar_wsb <- ar_wsb %>%
  left_join(ar_pwsids, by = c("objectid", "pws_name")) %>%
  # drop 12 geometries with no matching pwsid
  filter(!is.na(pwsid))

# Compute centroids, convex hulls, and radius assuming circular
ar_wsb <- ar_wsb %>%
  bind_rows() %>%
  mutate(
    state          = "AR",
    # importantly, area calculations occur in area weighted epsg
    st_areashape   = st_area(geometry),
    convex_hull    = st_geometry(st_convex_hull(geometry)),
    area_hull      = st_area(convex_hull),
    radius         = sqrt(area_hull/pi)
  ) %>%
  # transform back to standard epsg for geojson write
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
    pwsid,
    pws_name,
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

# create state dir in staging
dir_create(path(staging_path, "ar"))

# delete layer if it exists, then write to geojson
path_out <- path(staging_path, "ar/ar_wsb_labeled.geojson")
if(file_exists(path_out)) file_delete(path_out)

st_write(ar_wsb, path_out)
cat("Wrote clean, labeled data to geojson.\n\n\n") 