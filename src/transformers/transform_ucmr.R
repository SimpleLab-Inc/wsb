# transform UCMR3 and UCMR4 zip codes and add centroids ---------------------

library(fs)
library(sf)
library(tidyverse)
library(tigris)
options(tigris_use_cache = TRUE)

# helper function
source(here::here("src/functions/f_clean_whitespace_nas.R"))

# path to save raw data, staging data, and standard projection
data_path    <- Sys.getenv("WSB_DATA_PATH")
staging_path <- Sys.getenv("WSB_STAGING_PATH")
epsg         <- as.numeric(Sys.getenv("WSB_EPSG"))
epsg_aw      <- Sys.getenv("WSB_EPSG_AW")


# read ucmr3 and ucmr4 data
ucmr3 <- read.csv(path(data_path, "ucmr/UCMR3_ZipCodes.txt"), sep="\t", 
                  header = T, colClasses=c("ZIPCODE"="character")) 
ucmr4 <- read.csv(path(data_path, "ucmr/UCMR4_ZipCodes.txt"), sep="\t", 
                  header = T, colClasses=c("ZIPCODE"="character")) 


# Merge and do distinct
# Keep duplicate pwsids b/c they may serve more than one zipcode
ucmr <- ucmr3 %>% 
  bind_rows(ucmr4) %>%
  distinct() %>%
  janitor::clean_names() %>%
  mutate(zipcode = substr(zipcode, 1,5),
         zipcode = gsub("[^0-9.-]", "", zipcode)) %>%
  f_clean_whitespace_nas() %>%
  drop_na(zipcode) 

# merge zip codes to spatial zip code polygon
# zip code columns
cols_keep <- c("zipcode", "geoid10", 
               "aland10", "awater10", "geometry", "st_areashape",
               "centroid_x", "centroid_y", "area_hull", "radius")


# pull usa state geometries, project to input data CRS
zipcode_areas <- tigris::zctas()
zipcodes <- zipcode_areas %>% 
  janitor::clean_names() %>%
  st_transform(st_crs(epsg_aw)) %>% 
  mutate(
    # area calculations occur in area weighted epsg
    zipcode        = zcta5ce10,
    st_areashape   = st_area(geometry),
    centroid       = st_geometry(st_centroid(geometry)),
    centroid_x     = st_coordinates(centroid)[, 1],
    centroid_y     = st_coordinates(centroid)[, 2],
    convex_hull    = st_geometry(st_convex_hull(geometry)),
    area_hull      = st_area(convex_hull),
    radius         = sqrt(area_hull/pi)
  ) %>%
  select(all_of(cols_keep)) %>%
  # convert back to standard epsg
  st_transform(epsg) 

# join zipcode geography to ucmr master list
ucmr <- ucmr %>% 
  left_join(zipcodes, on = "zipcode")

# Write clean ucmr data to geojson
path_out <- path(staging_path, "ucmr.geojson")
if(file_exists(path_out)) file_delete(path_out)

st_write(ucmr, path_out)
