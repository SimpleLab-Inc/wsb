# preprocessing for model -------------------------------------------------

library(tidyverse)
library(tidymodels)
library(sf)
library(fs)

# data input location for modeling is the post-transformer staging path
staging_path <- Sys.getenv("WSB_STAGING_PATH")
data_path    <- Sys.getenv("WSB_DATA_PATH")
epsg         <- as.numeric(Sys.getenv("WSB_EPSG"))

# labeled boundaries
wsb_labeled <- st_read(path(staging_path, "wsb_labeled.geojson")) 

# j stands for joined data, read and rm rownumber column, then drop
# observations without a centroid
j <- read_csv(path(staging_path, "matched_output.csv"), col_select = -1) %>% 
  filter(!is.na(echo_latitude) | !is.na(echo_longitude)) 


