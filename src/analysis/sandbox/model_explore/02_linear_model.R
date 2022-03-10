# space to explore candidate models, characterize error, select features, and so on

# SWDIS water_system.csv continuous vars:
#   - population_served_count: rescale, likely to have high leverage
#   - service_connections_count
#   - we have zip code: perhaps we use this to pull census vars
#     or other vars like road density, population density, but we
#     are unsure of data quality of zip

# SDWIS water_system.csv categorical vars:
#   - is_wholesaler_ind: complete and can use
#   - primacy_type (state, territory, tribal): can't use because only 
#     "state" observations have labeled radii (not territory or tribal)
#   - primary_source_code: SW, GW, etc.

library(tidyverse)
library(tidymodels)
library(sf)
library(fs)

staging_path <- Sys.getenv("WSB_STAGING_PATH")
epsg_aw      <- Sys.getenv("WSB_EPSG_AW")
epsg         <- as.numeric(Sys.getenv("WSB_EPSG"))

d <- read_csv(path(staging_path, "matched_output_clean.csv"))
