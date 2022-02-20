# Transform EPA facility registry service data ---------------------------------

library(fs)
library(sf)
library(tidyverse)

# path to save raw data and standard projection
data_path    <- Sys.getenv("WSB_DATA_PATH")
staging_path <- Sys.getenv("WSB_STAGING_PATH")
epsg         <- Sys.getenv("WSB_EPSG")

# Read un-zipped geodatabase (~6GB so querying on water to reduce file size)
# First look at available layers
frs_layers <- st_layers(dsn = path(data_path, "frs/FRS_INTERESTS.gdb"))

#  SQL query to target facilities with water focus
get_water_frs <- 
  "SELECT * FROM FACILITY_INTERESTS WHERE INTEREST_TYPE 
   IN ('COMMUNITY WATER SYSTEM', 'NON-TRANSIENT NON-COMMUNITY WATER SYSTEM',
   'TRANSIENT NON-COMMUNITY WATER SYSTEM', 'WATER TREATMENT PLANT', 
   'DRINKING WATER PROGRAM', 'DRINKING WATER SYSTEM')"

# Read layer for FRS_INTERESTS with conditional query on `INTEREST_TYPE`
frs_water <- path(data_path, "frs/FRS_INTERESTS.gdb") %>% 
  st_read(query = get_water_frs, 
          layer = "FACILITY_INTERESTS", 
          stringsAsFactors = FALSE)

# Transform to standard epsg
frs_water <- frs_water %>% st_transform(crs = st_crs(epsg))
cat("Read labeled FRS layer and transformed to CRS:", epsg, ":\n ")

# Visualize points
plot(st_geometry(frs_water), pch = 1, col = 'blue')


# Clean up attribute data ------------------------------------------------------

# Set column names to lower case, split PWSID and Facility ID from pgm_sys_id
frs_water <- frs_water %>%
  janitor::clean_names() %>% 
  mutate(pwsid = word(pgm_sys_id, 1),
         facility_id = word(pgm_sys_id, 2),
         facility_id = ifelse(pwsid == facility_id, NA, facility_id))


# Write to geojson --------------------------------------------------------
path_out <- path(staging_path, "frs.geojson")
if(file_exists(path_out)) file_delete(path_out)

st_write(frs_water, path_out)
cat("Wrote FRS data to geojson. \n")
