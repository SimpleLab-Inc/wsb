# TODO: translate transform_echo.py into R for one contained script

library(fs)
library(sf)
library(tidyverse)

# source functions
dir_ls(here::here("src/functions")) %>% walk(~source(.x))

# path to save raw data and standard projection
data_path    <- Sys.getenv("WSB_DATA_PATH")
staging_path <- Sys.getenv("WSB_STAGING_PATH")
epsg         <- as.numeric(Sys.getenv("WSB_EPSG"))

# read in transformed echo csv
echo_file <- path(staging_path, "echo.csv")
echo <- read_csv(echo_file)

# change reported facility state colname to work with f_drop_imposters()
echo <- echo %>% mutate(state = fac_state)
                
# render lat/long as point geometry, first dropping missing lat/long
# unfortunately sf does not permit point formation with null coordinates
# so we will add the rest of the data (without coordinates) back in later.
# Create a spatial (sp) version of the echo table.
echo_sp <- echo  %>%
  filter(!is.na(fac_long) & !is.na(fac_lat)) %>%
  st_as_sf(coords = c("fac_long","fac_lat"), crs = epsg)

# clean imposters. First, create path for invalid geom log file.
path_log <- here::here("log", paste0(Sys.Date(), "-imposter-echo.csv"))

# drop imposters, sink a log file for review at the path above,
# and keep only relevant columns for the join back to echo tabular data
echo_sp_valid <- f_drop_imposters(echo_sp, path_log) %>% 
  select(registry_id, pwsid, geometry)

# collect imposters
imposters <- echo_sp %>%
  filter(!registry_id %in% echo_sp_valid$registry_id)

# registry ids of imposter geometries
ids_imposters <- unique(imposters$registry_id)

# starting with the full, tabular echo dataset:drop imposters, 
# join to valid geoms, and concert back into a spatial object
echo <- echo %>%
  # remove imposters
  filter(!registry_id %in% ids_imposters) %>% 
  # join spatially valid geometries (non-imposters)
  left_join(echo_sp_valid, by = c("registry_id", "pwsid")) %>%
  # convert back to spatial object before saving
  st_as_sf(crs = epsg)

# write clean echo data to geojson
path_out <- path(staging_path, "echo.geojson")
if(file_exists(path_out)) file_delete(path_out)

st_write(echo, path_out)
