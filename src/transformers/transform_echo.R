# transform ECHO data  -----------------------------------

library(fs)
library(sf)
library(tidyverse)

# source functions
dir_ls(here::here("src/functions")) %>% walk(~source(.x))

# helper function
source(here::here("src/functions/f_clean_whitespace_nas.R"))

# path to save raw data and standard projection
data_path       <- Sys.getenv("WSB_DATA_PATH")
echo_data_path  <- path(data_path, "echo")
echo_file       <- path(echo_data_path, "ECHO_EXPORTER.CSV")
staging_path    <- Sys.getenv("WSB_STAGING_PATH")
path_out        <- path(staging_path, "echo.geojson")
epsg            <- as.numeric(Sys.getenv("WSB_EPSG"))

cols <- c('REGISTRY_ID', 'FAC_NAME', 'FAC_NAME', 'FAC_STREET',
          'FAC_CITY', 'FAC_STATE', 'FAC_ZIP', 'FAC_COUNTY',
          'FAC_FIPS_CODE', 'FAC_LAT', 'FAC_INDIAN_CNTRY_FLG',
          'FAC_FEDERAL_FLG', 'FAC_LONG', 'FAC_COLLECTION_METHOD',
          'FAC_REFERENCE_POINT', 'FAC_ACCURACY_METERS',
          'FAC_DERIVED_HUC', 'FAC_MAJOR_FLAG', 'FAC_ACTIVE_FLAG',
          'FAC_QTRS_WITH_NC', 'SDWIS_FLAG', 'SDWA_IDS',
          'SDWA_SYSTEM_TYPES', 'SDWA_INFORMAL_COUNT',
          'SDWA_FORMAL_ACTION_COUNT', 'SDWA_COMPLIANCE_STATUS',
          'SDWA_SNC_FLAG', 'FAC_DERIVED_TRIBES', 'FAC_DERIVED_HUC',
          'FAC_DERIVED_WBD', 'FAC_DERIVED_STCTY_FIPS',
          'FAC_DERIVED_ZIP', 'FAC_DERIVED_CD113', 'FAC_DERIVED_CB2010',
          'FAC_PERCENT_MINORITY', 'FAC_POP_DEN', 'EJSCREEN_FLAG_US')

bool_cols = c('fac_major_flag', 'fac_active_flag', 'sdwis_flag',
              'sdwa_snc_flag', 'fac_indian_cntry_flg', 'fac_federal_flg',
              'ejscreen_flag_us')

# read in ECHO data and clean
echo <- read_csv(echo_file, col_select=cols) %>%
  # make column names lowercase
  rename_all(tolower) %>%
  # clean whitespace and nulls
  f_clean_whitespace_nas() %>%
  # drop duplicates
  unique() %>%
  # drop null SDWA_IDS
  filter(!is.na(sdwa_ids)) %>%
  # split space-delimited pwsid's in sdwa_ids into lists
  mutate(sdwa_ids = str_split(sdwa_ids, " ")) %>%
  # explode rows with multiple pwsid's
  unnest(sdwa_ids) %>%
  # rename sdwa_ids to pwsid
  rename(pwsid = sdwa_ids) %>%
  # for bool_cols, map N to 0, Y to 1, and '' to NaN
  mutate_at(bool_cols, recode, `N`=0, `Y`=1, .default=NaN)

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
if(file_exists(path_out)) file_delete(path_out)

st_write(echo, path_out)
