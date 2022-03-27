# combine temm tiers into one spatial layer and write ---------------------

cat("\n\nPreparing to combine/write spatial output for TEMM Tiers 1-3.\n")

library(tidyverse)
library(sf)
library(fs)
library(here)
library(glue)

staging_path <- Sys.getenv("WSB_STAGING_PATH")
epsg         <- as.numeric(Sys.getenv("WSB_EPSG"))


# load geometries for each tier -------------------------------------------

cat("Loading geometries for Tiers 1-3...") 

# Tier 1: ASSIMILATED labeled boundaries
t1 <- path(staging_path, "wsb_labeled_clean.geojson") %>% 
  st_read(quiet = TRUE) %>% 
  select(pwsid)

# Tier 2: MATCHED TIGER Place boundaries
t2 <- path(staging_path, "tigris_places_clean.geojson") %>% 
  st_read(quiet = TRUE) %>% 
  select(tiger_match_geoid = geoid)

# Tier 3: MODELED boundaries
t3 <- path(staging_path, "tier3_median.geojson") %>% 
  st_read(quiet = TRUE) %>% 
  select(pwsid)

cat("done.\n") 


# matched output and tier classification ----------------------------------

# columns to keep in final df
cols_select <- c(
  "pwsid", "pws_name", "primacy_agency_code", "state_code", "city_served", 
  "county_served", "population_served_count", "service_connections_count", 
  "service_area_type_code", "owner_type_code", "geometry_lat", 
  "geometry_long", "geometry_quality", "tiger_match_geoid", 
  "has_labeled_bound", "is_wholesaler_ind", "primacy_type",
  "primary_source_code", "tier")

# service connection count cutoff for community water systems
n_max <- 15

# read and format matched output
cat("Reading matched output...")

d <- read_csv(path(staging_path, "matched_output_clean.csv")) %>%
  mutate(
    # indicate the tier to use for each pwsid
    tier = case_when(
      has_labeled_bound == TRUE ~ "Tier 1",
      has_labeled_bound == FALSE & !is.na(tiger_match_geoid) ~ "Tier 2",
      has_labeled_bound == FALSE & is.na(tiger_match_geoid)  ~ "Tier 3"
    )
  ) %>% 
  # filter to CWS and assume each connection must serve at least 1 person
  # this drop 267 rows (0.5% of data)
  filter(service_connections_count >= n_max,
         population_served_count   >= n_max) %>% 
  # remove 834 rows (1.5% of data) not in contiguous US, mostly Puerto Rico
  filter(primacy_agency_code %in% state.abb) %>% 
  # select only relevant cols
  select(all_of(cols_select)) %>% 
  suppressMessages()

cat("done.\n") 


# combine tiers -----------------------------------------------------------

# Separate Tiers 1-3 from matched output, join to spatial data, and bind
dt1 <- d %>% filter(tier == "Tier 1") %>% left_join(t1) %>% st_as_sf()
dt2 <- d %>% filter(tier == "Tier 2") %>% left_join(t2) %>% st_as_sf() 
dt3 <- d %>% filter(tier == "Tier 3") %>% left_join(t3) %>% st_as_sf()

temm <- bind_rows(dt1, dt2, dt3)

cat("Combined a spatial layer using best available tiered data.\n")


# write to multiple output formats ----------------------------------------

# paths to write
path_geojson  <- here("temm_layer",     glue("{Sys.Date()}_temm.geojson"))
path_shp      <- here("temm_layer/shp", glue("{Sys.Date()}_temm.shp"))
path_csv      <- here("temm_layer",     glue("{Sys.Date()}_temm.csv"))

# write geojson, shp, and csv
st_write(temm, path_geojson, delete_dsn   = TRUE)
st_write(temm, path_shp,     delete_layer = TRUE)
temm %>% st_drop_geometry() %>% write_csv(path_csv)

cat("Wrote data to geojson, shp, csv.\n\n\n")
