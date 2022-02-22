# transform labeled water system data to standard model -------------------

library(fs)
library(sf)
library(tidyverse)

# path to save raw data, staging data, and standard projection
data_path    <- Sys.getenv("WSB_DATA_PATH")
staging_path <- Sys.getenv("WSB_STAGING_PATH")
epsg         <- Sys.getenv("WSB_EPSG")

# read labeled data, transform to standard epsg
f <- dir_ls(path(data_path, "boundary"), recurse = TRUE, glob = "*geojson")
cat("Detected", length(f), "labeled spatial datasets.")

d <- map(f, ~st_read(.x) %>% st_transform(epsg))
cat("Read", length(f), "labeled spatial datasets and transformed to CRS",
    epsg, ":\n ", paste(basename(f), collapse = "\n  "), "\n")

# validate equal CRS
map_chr(d, ~st_crs(.x)$input) %>% unique()

# columns to keep in the final dataframe
cols_keep <- c("pwsid", "gis_name", "population", "connections", 
               "state", "county", "source", "st_areashape", "owner",
               "centroid_x", "centroid_y", "area_hull", "radius", "geometry")

# combine into one dataframe, plus ad hoc cleaning
d <- d %>% 
  bind_rows() %>% 
  mutate(
    st_areashape   = st_area(geometry),
    centroid       = st_geometry(st_centroid(geometry)),
    centroid_x     = st_coordinates(centroid)[, 1],
    centroid_y     = st_coordinates(centroid)[, 2],
    convex_hull    = st_geometry(st_convex_hull(geometry)),
    area_hull      = st_area(convex_hull),
    radius         = sqrt(area_hull/pi),
    state          = str_sub(pwsid, 1, 2),
    # one pesky pwsid in NM with a weird pwsid that begins with "CR"
    state          = ifelse(state == "CR", "NM", state),
    source         = ifelse(is.na(source), "NIEPS Water Program", source),
    # fill in gis name with system names for OK
    # note that underlying data uses "service_area" for oregon's "gis_name"
    gis_name       = ifelse(!is.na(gis_name), gis_name, toupper(name)),
  ) %>%
  # remove extra geometries and largely empty or unimportant columns (for now!)
  select(all_of(cols_keep))
cat("Computed area, centroids, and radii from convex hulls.\n")
cat("Combined into one layer and added: state names,",
    "centroid lat/lng, and data sources.\n")

# note that OR data is very low - only 10 
table(d$state) %>% sort() %>% rev()
or <- d %>% filter(state == "OR")
plot(or$geometry, col = 'green')

# delete layer if it exists, then write to geojson 
path_out <- path(staging_path, "wsb_labeled.geojson")
if(file_exists(path_out)) file_delete(path_out)

st_write(d, path_out)
cat("Wrote clean, labeled data to geojson \n")
