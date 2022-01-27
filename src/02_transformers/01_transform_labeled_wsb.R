# transform labeled water system data to standard model

library(tidyverse)
library(here)
library(fs)
library(sf)

# projected metric coordinate reference system for calculations
cat("Defined standard projected CRS, 3310.\n")
epsg <- 3310

# read labeled data, transform to 3310, and make valid
f <- dir_ls(here("data/boundary"), recurse = TRUE, glob = "*geojson")
cat("Detected", length(f), "labeled spatial datasets.")

d <- map(f, ~st_read(.x) %>% st_transform(epsg))
cat("Read", length(f), "labeled spatial datasets and transformed to CRS",
    epsg, ":\n ", paste(f, collapse = "\n  "), "\n")

# validate equal CRS
map_int(d, ~st_crs(.x)$epsg) %>% unique()

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

# combine into one dataframe, plus ad hoc cleaning
d <- d %>% 
  bind_rows() %>% 
  mutate(state = str_sub(pwsid, 1, 2),
         # one pesky pwsid in NM with a weird pwsid that begins with "CR
         state = ifelse(state == "CR", "NM", state))
cat("Combined into one layer and added state names. \n")

# note that OR data is very low - only 10 
table(d$state) %>% sort() %>% rev()

# sanity checks
d[[3]]$convex_hull %>% plot(col = 'lightblue')
d[[3]]$geometry %>% plot(col = "green", add = TRUE)
d[[3]]$centroid %>% plot(col = 'red', pch = 3, add = TRUE)

# write in geojson and rds
st_write(d, here("staging/labeled.geojson"))
write_rds(d, here("staging/labeled.rds"))
cat("Wrote clean, labeled data to geojson and rds. \n")
