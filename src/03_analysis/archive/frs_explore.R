library(tidyverse)
library(here)
library(data.table)

cols_keep <- c("FAC_NAME", "SDWA_IDS", "SDWA_SYSTEM_TYPES", 
               "FAC_STATE", "FAC_LAT", "FAC_LONG", "FAC_COLLECTION_METHOD",
               "FAC_ACCURACY_METERS", "FAC_PERCENT_MINORITY", "FAC_POP_DEN")
echo <- here::here("data/ECHO/ECHO_EXPORTER.csv") %>% 
  data.table::fread(select = cols_keep) %>% 
  rename(PWSID = SDWA_IDS) %>% 
  filter(!is.na(PWSID))

head(echo, 1000) %>% View()

ef <- here::here("data/envirofacts/water_system.csv") %>% 
  data.table::fread()

# clean missing state names
ef %>% 
  mutate(STATE_CODE = ifelse(STATE_CODE == "", 
                             str_sub(PWSID, 1, 2),
                             STATE_CODE))

View(ef)
