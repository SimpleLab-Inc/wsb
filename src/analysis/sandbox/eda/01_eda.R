# EDA

library(tidyverse)
library(here)
library(fs)
library(sf)

# path to save raw data and standard projection
data_path    <- Sys.getenv("WSB_DATA_PATH")
staging_path <- Sys.getenv("WSB_STAGING_PATH")
epsg         <- Sys.getenv("WSB_EPSG")

# rowwise st_differnce() 

# do all FRS pwsids share the same geometry?
# frs <- path(staging_path, "frs.geojson") %>% st_read()
frs <- rename(frs, geometry = Shape)

frs <- frs_water


# all FRS 
ids <- frs %>% st_drop_geometry() %>% count(pwsid) %>% filter(n > 1) %>% pull(pwsid)


# show there are ~1.7% (~500 distinct lat/lng out of 32329 unqiue pwsid groups length(unique(frs$pwsid)) )
ids_distinct <- frs %>% 
  st_drop_geometry() %>% 
  filter(pwsid %in% ids) %>% 
  select(pwsid, primary_name, latitude83, longitude83) %>% 
  group_by(pwsid) %>% 
  summarise(
    nd_lat = n_distinct(latitude83), 
    nd_lon = n_distinct(longitude83)
  ) %>% 
  ungroup() %>%
  arrange(desc(nd_lat)) %>% 
  filter(nd_lat > 1 | nd_lon > 1) %>% 
  pull(pwsid)

# actually calcualte the differences
frs %>% 
  st_transform(3310) %>% 
  mutate(lat = st_coordinates(geometry)[, 1], 
         lon = st_coordinates(geometry)[, 2] 
  ) %>% 
  st_drop_geometry() %>% 
  filter(pwsid %in% ids_distinct) %>% 
  select(pwsid, lat, lon) %>% 
  group_by(pwsid) %>% 
  mutate(range_lat = diff(range(lat)), 
         range_lon = diff(range(lon))) %>% 
  ungroup() %>% 
  # 1 LA (9x SF) in surface area
  filter(range_lat > 35000 | range_lon > 35000) %>% View()
  pull(pwsid) 

frs %>% filter(pwsid == "CA1502034") %>% mapview::mapview()
frs %>% filter(pwsid == "AK2262351") %>% mapview::mapview()
frs %>% filter(pwsid == "TX1012759") %>% mapview::mapview()


# shows that ~10% of pwsids (395/3000ish) with > 1 distinct lat/lng (and 1% of all unique pwsid groups) have a 
# spatial spread (difference of range) that exceeds what we
# expect for a moderate sized city (9x area of SF)

# plot connection count against polygon area and convex hull area

# output plots of all polygons and convex hulls to visually inspect

# calculate percent increase in area from polygon to convex hull to
# estimate distribution of uncertainty in area imposed by this approach

# explore relationships between connection count and water system type
# (i.e., small, med, large)

# explore other predictors with presumed large explanatory power

