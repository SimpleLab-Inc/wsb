# Transform EPA facility registry service data ---------------------------------
library(sf)
library(tidyverse)
library(here)

# Read in un-zipped geodatabase file (~6GB so querying on water to bring down file size)
# First look at available layers
frs_layers <- st_layers(dsn = here("data/frs/FRS_INTERESTS.gdb"))

# Write SQL query to target facilities with water focus
get_water_frs <- "SELECT * FROM FACILITY_INTERESTS WHERE INTEREST_TYPE 
                IN ('COMMUNITY WATER SYSTEM', 'NON-TRANSIENT NON-COMMUNITY WATER SYSTEM',
                'TRANSIENT NON-COMMUNITY WATER SYSTEM', 'WATER TREATMENT PLANT', 
                'DRINKING WATER PROGRAM', 'DRINKING WATER SYSTEM')"

# Read in layer for FRS_INTERESTS with conditional query on `INTEREST_TYPE`
file_path = here("data/frs/FRS_INTERESTS.gdb")
frs_water <- st_read(file_path, query = get_water_frs, 
                     layer = "FACILITY_INTERESTS", stringsAsFactors = FALSE)

# Albers Equal Area Conic projected CRS for equal area calculations
# https://epsg.io/102003
# TODO: whenever we have AK and HI, we need to shift geometry into
# this CRS so area calculations are minimally distorted. 
# See `tigris::shift_geometry(d, preserve_area = TRUE)`
# https://walker-data.com/census-r/census-geographic-data-and-applications-in-r.html#shifting-and-rescaling-geometry-for-national-us-mapping
cat("Defined standard projected CRS, 102003.\n")
epsg <- "ESRI:102003"

# Transform to 102003, and make valid
d <- frs_water %>% st_transform(crs = st_crs(epsg))
cat("Read", length(f), "labeled FRS layer and transformed to CRS",
    epsg, ":\n ", paste(f, collapse = "\n  "), "\n")

# Visualize points
plot(st_geometry(d), pch = 1, col = 'blue')

# Clean up attribute data ------------------------------------------------------

# Set column names to lower case
names(d) <- tolower(names(d))

# Split out PWSID and Facility ID from pgm_sys_id
d <- d %>%
  mutate(pwsid = gsub( " .*$", "", d$pgm_sys_id),
         facility_id = gsub( "^\\S+\\s+", "", d$pgm_sys_id),
         facility_id = ifelse(pwsid == facility_id, NA, facility_id))

# Write in geojson and rds -----------------------------------------------------
st_write(d, here("staging/frs.geojson"))
write_rds(d, here("staging/frs.rds"))
cat("Wrote FRS data to geojson and rds. \n")

