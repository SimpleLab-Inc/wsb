# combine temm tiers into one spatial layer and write ---------------------

cat("\n\nPreparing to combine/write spatial output for TEMM Tiers 1-3.\n")

library(tidyverse)
library(sf)
library(fs)
library(here)
library(glue)

staging_path <- Sys.getenv("WSB_STAGING_PATH")
output_path <- Sys.getenv("WSB_OUTPUT_PATH")
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

# Tier 3: MODELED boundaries - use median result geometry but bring in CIs
t3 <- path(staging_path, "tier3_median.geojson") %>% 
  st_read(quiet = TRUE) %>% 
  select(pwsid, 
         pred_05 = .pred_lower, 
         pred_50 = .pred,
         pred_95 = .pred_upper)

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

# read and format matched output
cat("Reading matched output...")

d <- read_csv(path(staging_path, "matched_output_clean.csv")) %>%
  mutate(
    # indicate the tier to use for each pwsid
    tier = case_when(
      has_labeled_bound == TRUE ~ "Tier 1",
      has_labeled_bound == FALSE & tiger_to_pws_match_count == 1 ~ "Tier 2a",
      has_labeled_bound == FALSE & tiger_to_pws_match_count >  1 ~ "Tier 2b",
      has_labeled_bound == FALSE & is.na(tiger_match_geoid)  ~ "Tier 3"
    )
  ) %>% 
  # select only relevant cols
  select(all_of(cols_select)) %>% 
  suppressMessages()

cat("done.\n") 


# combine tiers -----------------------------------------------------------

# Separate Tiers 1-3 from matched output, join to spatial data, and bind
dt1 <- d %>% filter(tier == "Tier 1") %>% left_join(t1) %>% st_as_sf()
dt2 <- d %>% filter(tier %in% c("Tier 2a", "Tier 2b")) %>% left_join(t2) %>% st_as_sf() 
dt3 <- d %>% filter(tier == "Tier 3") %>% left_join(t3) %>% st_as_sf()

temm <- bind_rows(dt1, dt2, dt3)

cat("Combined a spatial layer using best available tiered data.\n")


# write to multiple output formats ----------------------------------------

# paths to write
path_geojson  <- path(output_path, "temm_layer", glue("{Sys.Date()}_temm.geojson"))
path_shp      <- path(output_path, "temm_layer/shp", glue("{Sys.Date()}_temm.shp"))
path_csv      <- path(output_path, "temm_layer",     glue("{Sys.Date()}_temm.csv"))

# create dirs
dir_create(path(output_path, "temm_layer"))
dir_create(path(output_path, "temm_layer/shp"))

# write geojson, shp, and csv
st_write(temm, path_geojson, delete_dsn   = TRUE)
st_write(temm, path_shp,     delete_layer = TRUE)
temm %>% st_drop_geometry() %>% write_csv(path_csv)

cat("Wrote data to geojson, shp, csv.\n\n\n")
