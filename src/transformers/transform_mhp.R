# Transform mobile home park point data  ---------------------------------------

library(fs)
library(sf)
library(tidyverse)
library(mltools)


# path to save raw data and standard projection
data_path    <- Sys.getenv("WSB_DATA_PATH")
staging_path <- Sys.getenv("WSB_STAGING_PATH")
epsg         <- Sys.getenv("WSB_EPSG")


# Read un-zipped geodatabase (~6GB so querying on water to reduce file size)
# First look at available layers
mhp_sp <- st_read(dsn = path(data_path, "boundary/mhp/mhp.geojson"))

# Transform to standard epsg
mhp_sp <- mhp_sp %>% st_transform(crs = st_crs(epsg))
cat("Read labeled FRS layer and transformed to CRS:", epsg, ":\n ")

# Visualize points
plot(st_geometry(mhp_sp), pch = 1, col = 'blue')

# Clean up attribute data ------------------------------------------------------
# Set column names to lower
names(mhp_sp) <- tolower(names(mhp_sp))

# One hot encode categorical variables ----------------------------------------- 
# Size and units should be correlated, but a frequent units value is -999
# So categorical grouping may be more efficient
# One hot encode categorical and use NA for unknowns (instead of -999)

mhp_sp <- mhp_sp %>% 
  mutate(size = as.factor(tolower(size)),
         units = na_if(units, -999)) %>%
  as.data.table() %>%
  # one hot encode variables set as factors
  one_hot() %>%
  as.data.frame() %>%
  # clean up column names
  select(
    object_id  = objectid,
    mhp_id     = mhpid,
    mhp_name   = name,
    address,
    city,
    state,
    zipcode    = zip,
    zip4,
    telephone,
    status,
    county,
    county_fips = countyfips,
    country,
    latitude,
    longitude,
    naics_code,
    naics_desc,
    source,
    source_date = sourcedate,
    val_method,
    val_date,
    website,
    units,
    size_large   = `size_large (>100)`,
    size_medium  = `size_medium (51-100)`,
    size_small   = `size_small (<50)`,
    rev_geo_flag = revgeoflag,
    geometry
  )

# Write clean mobile home park centroids
path_out <- path(staging_path, "mhp_clean.geojson")
if(file_exists(path_out)) file_delete(path_out)

st_write(mhp_sp, path_out)
