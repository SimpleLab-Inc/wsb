
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
                
# render lat/long as point geometry, first dropping missing lat/long
# unfortunately sf does not permit point formation with null coordinates
# so we'll need to add the rest of the data in later
echo_sp <- echo %>%
  # move this step to python transformer
  mutate(state = fac_state) %>%
  filter(!is.na(fac_long) & !is.na(fac_lat)) %>%
  st_as_sf(., coords = c("fac_long","fac_lat"), crs = epsg)

# clean invalid geometries. First, create path for invalid geom log file.
path_log <- here::here("log", paste0(Sys.Date(), "-imposter-echo.csv"))

# drop invalid geometries and sink a log file for review at the path above.
echo_sp_imp <- f_drop_imposters(echo_sp, path_log)

# collect imposters 
imposters <- echo_sp %>%
  filter(!(registry_id %in% echo_sp_imp$registry_id))

# drop imposters from full dataset and join valid geoms
echo <- echo %>%
  # remove imposters
  filter(!(registry_id %in% imposters$registry_id)) %>%
  # join spatially valid geometries to filtered echo dataset
  left_join(echo_sp_imp %>% select(registry_id, pwsid, geometry), 
            on = c("registry_id", "pwsid"))

# write clean echo data to geojson
path_out <- path(staging_path, "echo.geojson")
if(file_exists(path_out)) file_delete(path_out)

st_write(echo, path_out)
