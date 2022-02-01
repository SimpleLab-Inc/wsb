# Transform EPA facility registry service data ---------------------------------
library(sf)
library(tidyverse)
library(here)

# Read un-zipped geodatabase (~6GB so querying on water to reduce file size)
# First look at available layers
frs_layers <- st_layers(dsn = here("data/frs/FRS_INTERESTS.gdb"))

#  SQL query to target facilities with water focus
get_water_frs <- 
  "SELECT * FROM FACILITY_INTERESTS WHERE INTEREST_TYPE 
   IN ('COMMUNITY WATER SYSTEM', 'NON-TRANSIENT NON-COMMUNITY WATER SYSTEM',
   'TRANSIENT NON-COMMUNITY WATER SYSTEM', 'WATER TREATMENT PLANT', 
   'DRINKING WATER PROGRAM', 'DRINKING WATER SYSTEM')"

# Read layer for FRS_INTERESTS with conditional query on `INTEREST_TYPE`
frs_water <- here("data/frs/FRS_INTERESTS.gdb") %>% 
  st_read(query = get_water_frs, 
          layer = "FACILITY_INTERESTS", 
          stringsAsFactors = FALSE)

# Albers Equal Area Conic projected CRS for equal area calculations
# https://epsg.io/102003
# TODO: whenever we have AK and HI, we need to shift geometry into
# this CRS so area calculations are minimally distorted. 
# See `tigris::shift_geometry(d, preserve_area = TRUE)`
# https://walker-data.com/census-r/census-geographic-data-and-applications-in-r.html#shifting-and-rescaling-geometry-for-national-us-mapping
epsg <- "ESRI:102003"
cat("Defined standard projected CRS:", epsg, "\n")

# Transform to standard epsg
frs_water <- frs_water %>% st_transform(crs = st_crs(epsg))
cat("Read labeled FRS layer and transformed to CRS:", epsg, ":\n ")

# Visualize points
plot(st_geometry(frs_water), pch = 1, col = 'blue')

# Clean up attribute data ------------------------------------------------------

# Set column names to lower case, split PWSID and Facility ID from pgm_sys_id
frs_water <- frs_water %>%
  janitor::clean_names(frs_water) %>% 
  mutate(pwsid = word(pgm_sys_id, 1),
         facility_id = word(pgm_sys_id, 2),
         facility_id = ifelse(pwsid == facility_id, NA, facility_id))

# Write to geojson and rds -----------------------------------------------------
fs::file_delete(here("staging/frs.geojson"))
st_write(frs_water, here("staging/frs.geojson"))
write_rds(frs_water, here("staging/frs.rds"))
cat("Wrote FRS data to geojson and rds. \n")
