# transform IL water system data to standard model -------------------

cat("Preparing to transform IL polygon boundary data.\n\n")

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

# Read layer for IL water service boundaries, clean, transform CRS
il_wsb <- st_read(
  dsn = path(data_path, "boundary/il/Illinois_Municipal_Water_use_2012/Municipal_Water_Use_Statewide.gdb"),
  layer = "Municipal_Use_2012") %>% 
  rename(geometry = "Shape") %>%
  # clean whitespace
  f_clean_whitespace_nas() %>%
  # transform to area weighted CRS
  st_transform(epsg_aw) %>%
  # correct invalid geometries
  st_make_valid() %>%
  janitor::clean_names()

cat("Read IL boundary layer; cleaned whitespace; corrected geometries.\n ")

# Compute centroids, convex hulls, and radius assuming circular
# Combine data and merge geometries for rows with duplicate pwsids
il_wsb <- il_wsb %>%
  mutate(
    state          = "IL",
    # 161 cities have no pwsid listed
    # Of these, 123 have a seller pwsid listed
    pwsid          = if_else(is.na(fac_id), seller_fac_id, fac_id),
    # Facility id blank = seller system, with name in "buys from"
    # Spot checking on name_1 for cases where fac_id is listed looks consistent
    pws_name       = if_else(!is.na(fac_id), buys_from, name_1),
    # Preliminary geometry calculations 
    # Calculate area sums and convex hulls
    st_areashape   = st_area(geometry),
    convex_hull    = st_geometry(st_convex_hull(geometry)),
    area_hull      = st_area(convex_hull),
  ) %>%
  group_by(pwsid) %>% 
  # mutate these new columns, knowing full well that duplicate rows
  # will be created, but that they will be dropped in the next step
  mutate(
    # combine all fragmented geometries
    geometry       = st_union(geometry),
    # new area is the sum of the area of all polygons
    st_areashape   = sum(st_areashape),
    area_hull      = sum(area_hull),
    # new radius is calculated from the new area
    radius         = sqrt(area_hull/pi),
    # combine data into list-formatted strings for character columns
    across(where(is.character), ~toString(unique(.)))
  ) %>%
  # only take the first result from each group
  slice(1) %>%
  ungroup() %>% 
  # convert back to the project standard epsg
  st_transform(epsg) %>% 
  # compute new centroids and note that when multipolygons are separated
  # by space, these are suspect and should not be used. Importantly, this
  # calculation occurs in the EPSG consistent with other staged data!
  mutate(
    centroid       = st_geometry(st_centroid(geometry)),
    centroid_long  = st_coordinates(centroid)[, 1],
    centroid_lat   = st_coordinates(centroid)[, 2]
  ) %>% 
  # select columns and rename for staging
  select(
    # data source columns
    pwsid,         
    pws_name,      
    state,
    #    county,
    city            = name_1,
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

# verify that there is only one pwsid per geometry
n <- il_wsb %>%
  count(pwsid) %>%
  filter(n > 1) %>%
  nrow()
cat(n, "duplicate pwsids in labeled data following fix.\n")

# delete layer if it exists, then write to geopackage
path_out <- path(staging_path, "wsb_labeled_il.gpkg")
if(file_exists(path_out)) file_delete(path_out)

st_write(il_wsb, path_out)
cat("Wrote clean, labeled data to file.\n\n\n") 
