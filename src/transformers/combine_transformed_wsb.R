# combine transformed state water system data ------------------------

library(fs)
library(sf)
library(tidyverse)

# path to save raw data, staging data, and standard projection
staging_path <- Sys.getenv("WSB_STAGING_PATH")

# list, read, and combine all staged state wsb files
wsb <- list.files(path = staging_path, 
                  pattern = "_wsb_labeled.geojson$", 
                  recursive = TRUE) %>% 
  map_df(~st_read(path(staging_path, .)))


# delete layer if it exists, then write to geojson
path_out <- path(staging_path, "wsb_labeled.geojson")
if(file_exists(path_out)) file_delete(path_out)

st_write(nm_wsb, path_out)
cat("Wrote clean, labeled data to geojson.\n")
