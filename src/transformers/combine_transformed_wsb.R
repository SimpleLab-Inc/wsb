# combine transformed state water system data ----------------------------

library(fs)
library(sf)
library(tidyverse)
library(mapview)

# path to save staging data and standard projection
staging_path <- Sys.getenv("WSB_STAGING_PATH")
epsg_aw      <- Sys.getenv("WSB_EPSG_AW")
epsg         <- as.numeric(Sys.getenv("WSB_EPSG"))

# list, read, and combine all staged state wsb files
wsb_labeled <- list.files(path = staging_path, 
                          pattern = "_wsb_labeled.geojson$", 
                          recursive = TRUE) %>% 
  map_df(~st_read(path(staging_path, .))) %>% 
  # remove NA pwsid
  filter(!is.na(pwsid))

# combine data and merge geometries for rows with duplicate pwsids --------

# show there are rows with duplicate pwsids
multi <- st_drop_geometry(wsb_labeled) %>% 
  count(pwsid, sort = TRUE) %>% 
  filter(n > 1)
multi
cat("Detected", nrow(multi), "multipolygon pwsid groups.\n")

# add column indicating if row has a duplicated pwsid
wsb_labeled <- wsb_labeled %>% 
  # label multipolygon geometries
  mutate(is_multi = ifelse(pwsid %in% multi$pwsid, TRUE, FALSE))
cat("Added `is_multi` field to wsb labeled data.\n")

# separate rows without duplicated pwsid's
wsb_labeled_no_multi <- wsb_labeled %>% 
  filter(is_multi == FALSE)

# for rows with duplicated pwsids: 
# union geometries, recalculate area, centroids, radius
wsb_labeled_multi <- wsb_labeled %>% 
  # filter for rows with duplicated pwsid's
  filter(is_multi == TRUE) %>% 
  st_make_valid() %>% 
  # importantly, all calculations take place in AW epsg 
  st_transform(epsg_aw) %>% 
  group_by(pwsid) %>% 
  summarise(
    # combine all fragmented geometries into multipolygons
    geometry     = st_union(geometry),
    # new area is the sum of the area of all polygons
    st_areashape = sum(st_areashape),
    area_hull    = sum(area_hull),
    # new radius is calculated from the new area
    radius       = sqrt(area_hull/pi)
  ) %>% 
  ungroup() %>% 
  # convert back to the project standard epsg
  st_transform(epsg) %>% 
  # compute new centroids
  # note: when multipolygons are separated by space, these are suspect
  mutate(
    centroid       = st_geometry(st_centroid(geometry)),
    centroid_long  = st_coordinates(centroid)[, 1],
    centroid_lat   = st_coordinates(centroid)[, 2],
  ) %>% 
  # remove centroid column
  select(-centroid)
cat("Recalculated area, radius, centroids for multipolygon pwsids.\n")

# view
# mapview::mapview(wsb_labeled_multi, zcol = "pwsid", burst = TRUE)

# combine wsb labeled data with corrected rows
wsb_labeled_clean <- bind_rows(wsb_labeled_no_multi, wsb_labeled_multi) 
cat("Joined multipolygon and no multi-polygon data into one object.\n")

# verify that there is only one pwsid per geometry
n <- wsb_labeled_clean %>% 
  st_drop_geometry() %>% 
  count(pwsid) %>% 
  filter(n > 1) %>% 
  nrow()
cat(n, "duplicate pwsid in labeled data following multipolygon fix.\n")

# delete layer if it exists, then write to geojson
path_out <- path(staging_path, "wsb_labeled_clean.geojson")
if(file_exists(path_out)) file_delete(path_out)

st_write(wsb_labeled_clean, path_out)
cat("Wrote clean, labeled data to geojson.\n")
