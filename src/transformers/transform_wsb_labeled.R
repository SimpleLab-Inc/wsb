# transform labeled water system data to standard model

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

# compute centroids, convex hulls, and radius assuming circluar area
d <- map(
  d, 
  ~mutate(
    .x, 
    centroid    = st_geometry(st_centroid(geometry)),
    convex_hull = st_geometry(st_convex_hull(geometry)),
    area_hull   = st_area(convex_hull),
    radius      = sqrt(area_hull/pi)
  )
)
cat("Computed centroids, convex hulls, and radii. \n")

# sanity checks
d[[3]]$convex_hull %>% plot(col = 'lightblue')
d[[3]]$geometry %>% plot(col = "green", add = TRUE)
d[[3]]$centroid %>% plot(col = 'red', pch = 3, add = TRUE)

# combine into one dataframe, plus ad hoc cleaning
d <- d %>% 
  bind_rows() %>% 
  mutate(state = str_sub(pwsid, 1, 2),
         # one pesky pwsid in NM with a weird pwsid that begins with "CR"
         state = ifelse(state == "CR", "NM", state))
cat("Combined into one layer and added state names. \n")

# note that OR data is very low - only 10 
table(d$state) %>% sort() %>% rev()

# delete layer if it exsits, then write to geojson 
path_out <- path(staging_path, "wsb_labeled.geojson")
if(file_exists(path_out)) file_delete(path_out)

st_write(d, path_out)
cat("Wrote clean, labeled data to geojson and rds. \n")
