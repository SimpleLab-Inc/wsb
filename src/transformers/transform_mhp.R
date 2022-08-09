# Transform mobile home park point data  ----------------------------------

library(fs)
library(sf)
library(tidyverse)

# helper functions
dir_ls(here::here("src/functions")) %>% walk(~source(.x))

# path to save raw data and standard projection
data_path    <- Sys.getenv("WSB_DATA_PATH")
staging_path <- Sys.getenv("WSB_STAGING_PATH")
epsg         <- as.numeric(Sys.getenv("WSB_EPSG"))

# Read un-zipped geodatabase, clean names, transform to standard epsg
mhp_sp <- st_read(dsn = path(data_path, "mhp/mhp.geojson")) %>% 
  janitor::clean_names() %>% 
  st_transform(crs = epsg)

cat("Read MHP layer, cleaned names, & transformed to CRS:", epsg, "\n ")

# Visualize points
#plot(st_geometry(mhp_sp), pch = 1, col = 'blue')


# Clean attribute data ----------------------------------------------------

mhp_sp <- mhp_sp %>% 
  # clean size column and replace -999 missing units with NA
  mutate(size  = as.factor(tolower(size)),
         units = na_if(units, -999)) %>%
  # clean column names
  rename(
    object_id    = objectid,
    mhp_id       = mhpid,
    mhp_name     = name,
    zipcode      = zip,
    county_fips  = countyfips,
    source_date  = sourcedate,
    rev_geo_flag = revgeoflag
  ) %>% 
  f_clean_whitespace_nas()

# Write clean mobile home park centroids
path_out <- path(staging_path, "mhp_clean.geojson")
if(file_exists(path_out)) file_delete(path_out)

st_write(mhp_sp, path_out)
