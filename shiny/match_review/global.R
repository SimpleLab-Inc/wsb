library(here)
library(leaflet)
library(tidyverse)
library(sf)
library(fs)
library(shiny)
library(DT)

# path to save raw data and standard projection
staging_path <- Sys.getenv("WSB_STAGING_PATH")

# matched data - read as GEOJSON from the project folder "output" dir
dmatch <- here("output/stacked_match_report.geojson") %>% st_read()

# all unique pwsids to include in dropdown select menu
pwsids <- dmatch$mk_match %>% unique() 
