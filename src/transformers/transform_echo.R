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
path_out        <- path(staging_path, "echo.csv")

cols <- c('REGISTRY_ID', 'FAC_NAME', 'FAC_NAME', 'FAC_STREET',
          'FAC_CITY', 'FAC_STATE', 'FAC_ZIP', 'FAC_COUNTY',
          'FAC_FIPS_CODE', 'FAC_LAT', 'FAC_LONG', 'FAC_INDIAN_CNTRY_FLG',
          'FAC_FEDERAL_FLG',  'FAC_COLLECTION_METHOD',
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
  janitor::clean_names() %>% 
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
  mutate_at(bool_cols, recode, `N`=0, `Y`=1, .default=NaN) %>%
  # convert bool_cols to boolean type
  mutate_at(bool_cols, as.logical)

# Delete output file if exists
if(file_exists(path_out)) file_delete(path_out)

# Drop geometry and write as a CSV
echo %>% write_csv(path_out)
