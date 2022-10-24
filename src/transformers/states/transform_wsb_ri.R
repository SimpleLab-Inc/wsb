# Transform RI water system data to standard model -------------------

cat("Preparing to transform RI polygon boundary data.\n\n")

library(fs)
library(sf)
library(tidyverse)

# Helper function
source(here::here("src/functions/f_clean_whitespace_nas.R"))

# Path to save raw data, staging data, and standard projection
data_path    <- Sys.getenv("WSB_DATA_PATH")
staging_path <- Sys.getenv("WSB_STAGING_PATH")
epsg         <- as.numeric(Sys.getenv("WSB_EPSG"))
epsg_aw      <- Sys.getenv("WSB_EPSG_AW")

# Read manually curated list of pwsids developed by EPIC to link shapefiles for
# water districts with water systems (see here: https://docs.google.com/spreadsheets/d/13aVFXj9Ty5EsRNFuHczpX04HoCzc689LVGKcJIREXY4/edit#gid=0)
pwsid_lookup <- read.csv(here::here("crosswalks/ri_pwsid_lookup.csv")) %>%
  select(PWSID, H20_DISTRI, NAME, pws_name)

# Read layer for AZ water service boundaries, clean, transform CRS
ri_wsb <- st_read(path(data_path, "boundary/ri/ri.geojson")) %>% 
  # clean whitespace
  f_clean_whitespace_nas() %>%
  # transform to area weighted CRS
  st_transform(epsg_aw) %>%
  # calculate geometries and areas of individual polygons
  mutate(
    state          = "RI",
    # area calculations occur in area weighted epsg
    st_areashape   = st_area(geometry),
    convex_hull    = st_geometry(st_convex_hull(geometry)),
    area_hull      = st_area(convex_hull)
  ) 

cat("Read RI boundary layer; cleaned whitespace; corrected geometries.\n")

ri_wsb <- ri_wsb %>%
  # join to pwsids
  left_join(pwsid_lookup, on = c("H20_DISTRI", "NAME")) %>%
  # clean up names
  janitor::clean_names() %>%
  # only keep boundaries with a pwsid (others are GW/SW sources it appears)
  filter(!is.na(pwsid)) %>%
  # group by pwsid to calculate total area based in multipolygons
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
  # correct invalid geometries
  st_make_valid() %>%
  # compute new centroids and note that when multipolygons are separated
  # by space, these are suspect and should not be used. Importantly, this
  # calculation occurs in the EPSG consistent with other staged data!


  # Strangely, this step fails when run from run_pipeline in an ipykernel.
  # The error is "Found 1 feature with invalid spherical geometry."
  # But I thought st_make_valid should've solved this.
  # The workaround is to run this step manually from R.
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
    county,       
    # geospatial columns
    st_areashape,
    centroid_long,
    centroid_lat,
    radius,
    geometry
  )

cat("Recalculated area, radius, centroids for multipolygon pwsids.\n")
cat("Combined string values for multipolygon pwsids.\n")

# verify that there is only one pwsid per geometry
n <- ri_wsb %>%
  count(pwsid) %>%
  filter(n > 1) %>%
  nrow()
cat(n, "duplicate pwsids in labeled data following fix.\n")


# delete layer if it exists, then write to geopackage
path_out <- path(staging_path, "wsb_labeled_ri.gpkg")
if(file_exists(path_out)) file_delete(path_out)

st_write(ri_wsb, path_out)