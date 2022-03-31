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

cat("Removed", nrow(zip_rm), "nonsense zipcodes from ucmr data.\n")


# merge zip codes to spatial zip code polygon -----------------------------

# zip code columns to keep
cols_keep <- c("zipcode", "geoid20", "aland20", "awater20", "st_areashape",
               "area_hull")

# pull usa state geometries, project to input data CRS
zipcode_areas <- tigris::zctas()
zipcodes <- zipcode_areas %>% 
  janitor::clean_names() %>%
  # use area weighted crs because we calculate polygon areas
  st_transform(st_crs(epsg_aw)) %>% 
  mutate(
    # area calculations occur in area weighted epsg
    zipcode        = zcta5ce20,
    st_areashape   = st_area(geometry),
    convex_hull    = st_geometry(st_convex_hull(geometry)),
    area_hull      = st_area(convex_hull)
  ) %>% 
  select(all_of(cols_keep))


# join zipcode polygon geometries to ucmr master list and
# combine data and merge geometries for rows with duplicate pwsids --------

ucmr <- ucmr %>% 
  left_join(zipcodes, on = "zipcode") %>% 
  # convert object back to spatial
  st_as_sf(crs = epsg_aw) %>% 
  # ensure valid geometries
  st_make_valid() %>%
  group_by(pwsid) %>% 
  # mutate these new columns, knowing full well that duplicate rows
  # will be created, but that they will be dropped in the next step
  mutate(
    # combine all fragmented geometries
    geometry       = st_union(geometry),
    # new area is the sum of the area of all polygons
    st_areashape   = sum(st_areashape),
    area_hull      = sum(area_hull),
    # new radius is calculated from the new area
    radius         = sqrt(area_hull/pi),
    # combine data into list-formatted strings for character columns
    across(where(is.character), ~toString(unique(.)))
  ) %>%
  # only take the first result from each group
  slice(1) %>%
  ungroup() %>% 
  # convert back to the project standard epsg
  st_transform(epsg) %>% 
  # compute new centroids and note that when multipolygons are separated
  # by space, these are suspect and should not be used. Importantly, this
  # calculation occurs in the EPSG consistent with other staged data!
  mutate(
    centroid       = st_geometry(st_centroid(geometry)),
    centroid_long  = st_coordinates(centroid)[, 1],
    centroid_lat   = st_coordinates(centroid)[, 2]
  ) %>% 
  # remove columns. Note: future iteration may include other values downstream
  select(c(pwsid, zipcode, st_areashape, radius, centroid_long, centroid_lat)) %>%
  st_drop_geometry()

cat("Recalculated area, radius, centroids for multipolygon pwsids.\n")
cat("Combined string values for multipolygon pwsids.\n")

# verify that there is only one pwsid per geometry
n <- ucmr %>%
  count(pwsid) %>%
  filter(n > 1) %>%
  nrow()
cat(n, "duplicate pwsids in labeled data following fix.\n")


# Write clean ucmr data to geojson
path_out <- path(staging_path, "ucmr.csv")
if(file_exists(path_out)) file_delete(path_out)

write_csv(ucmr, path_out)
