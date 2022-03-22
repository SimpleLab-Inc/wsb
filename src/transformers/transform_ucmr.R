# transform UCMR3 and UCMR4 zip codes and add centroids ---------------------

library(fs)
library(sf)
library(tidyverse)
library(tigris)

# tell tigris to cache Census shapefile downloads for faster subsequent runs
options(tigris_use_cache = TRUE)

# helper function
source(here::here("src/functions/f_clean_whitespace_nas.R"))

# path to save raw data, staging data, and standard projection
data_path    <- Sys.getenv("WSB_DATA_PATH")
staging_path <- Sys.getenv("WSB_STAGING_PATH")
epsg         <- as.numeric(Sys.getenv("WSB_EPSG"))
epsg_aw      <- Sys.getenv("WSB_EPSG_AW")

# read ucmr3 and ucmr4 data, combine, clean names, add 
ucmr <- dir_ls(path(data_path, "ucmr"), regexp = "ZipCodes.txt") %>% 
  read_tsv(col_types = "c") %>% 
  distinct() %>% 
  janitor::clean_names() %>% 
  # a number of zipcodes end in "-" and should be cleaned
  mutate(zipcode = str_replace_all(zipcode, "-", "")) %>% 
  # clean whitespace and NAs, and drop NA zipcodes
  f_clean_whitespace_nas() %>%
  drop_na(zipcode) 

# print nonsense zipcodes for review because they're few in number. 
# zip codes should have exactly 5 digits and no alphabetical chars
zip_rm <- filter(ucmr, 
                 nchar(zipcode) != 5 | 
                 str_detect(zipcode, "[:alpha:]"))

cat("Detected", nrow(zip_rm), "nonsense zipcodes:\n"); print(zip_rm)

# remove nonsense zipcodes
ucmr <- anti_join(ucmr, zip_rm)

cat("Removed", nrow(zip_rm), "nonsense zipcodes from ucrm data.\n")


# merge zip codes to spatial zip code polygon -----------------------------

# zip code columns to keep
cols_keep <- c("zipcode", "geoid10", "aland10", "awater10", "st_areashape",
               "centroid_long", "centroid_lat", "area_hull", "radius")

# pull usa state geometries, project to input data CRS
zipcode_areas <- tigris::zctas()
zipcodes <- zipcode_areas %>% 
  janitor::clean_names() %>%
  # use area weighted crs because we calculate polygon areas
  st_transform(st_crs(epsg_aw)) %>% 
  mutate(
    # area calculations occur in area weighted epsg
    zipcode        = zcta5ce10,
    st_areashape   = st_area(geometry),
    convex_hull    = st_geometry(st_convex_hull(geometry)),
    area_hull      = st_area(convex_hull),
    radius         = sqrt(area_hull/pi)
  ) %>%
  # transform back to standard epsg for geojson write
  st_transform(epsg) %>%
  # compute centroids
  mutate(
    centroid       = st_geometry(st_centroid(geometry)),
    centroid_long  = st_coordinates(centroid)[, 1],
    centroid_lat   = st_coordinates(centroid)[, 2],
  ) %>%
  select(all_of(cols_keep))

# join zipcode polygon geometries to ucmr master list 
ucmr <- ucmr %>% 
  left_join(zipcodes, on = "zipcode") %>% 
  # convert object back to spatial
  st_as_sf(crs = epsg)

# Write clean ucmr data to geojson
path_out <- path(staging_path, "ucmr.geojson")
if(file_exists(path_out)) file_delete(path_out)

st_write(ucmr, path_out)
