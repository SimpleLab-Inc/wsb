# preprocess data for model -----------------------------------------------

library(tidyverse)
library(sf)
library(fs)

staging_path <- Sys.getenv("WSB_STAGING_PATH")
epsg_aw      <- Sys.getenv("WSB_EPSG_AW")
epsg         <- as.numeric(Sys.getenv("WSB_EPSG"))

# j stands for joined data, read and rm rownumber column, then drop
# observations without a centroid or with nonsensical service connections
j <- read_csv(path(staging_path, "matched_output.csv"), 
              col_select = -1) %>% 
  filter(!is.na(echo_latitude) | !is.na(echo_longitude)) %>% 
  # we also filter out 0 service connection count systems - 267 (0.4%), 
  # this should be cleaned/imputed in the transformer
  filter(service_connections_count > 0) 
cat("Read", nrow(j), 
    "matched outputs with nonzero service connection count.\n")


# mean impute population_served == 0 with linear model --------------------

# A 2022-03-08 meeting with IoW/BC/EPIC recommended filtering out 
# wholesalers and water systems with a zero population count. However, 
# many water systems have low population counts (e.g., between 0 and 10), 
# but very high service connection count (e.g., in the hundreds to 
# thousands), and wholesalers in labeled data are primarily found in WA 
# and TX. Thus, we retain all observations and mean impute nonsensical
# (between 0 and N) population counts.

# this is the critical population served count below which (inclusive) we
# assume that the value is nonsensical, and impute it based on the service
# connection count, which tends to be present and more correct.
n_max <- 10
cat("Preparing to mean impute population served count", 
    "for all population <=", n_max, ".\n")

# we learned in the Feb 2022 EDA (sandbox/eda/eda_february.Rmd) that
# population served and service connection count had outliers that were 
# likely incorrect. Here we highlight "bad" high leverage points
# j %>%
#   mutate(
#     grp = ifelse(
#       population_served_count %in% 0:n_max, "bad", "good"
#     )
#   ) %>%
#   ggplot(aes(service_connections_count, population_served_count)) +
#   geom_point(aes(color = grp), alpha = 0.5) +
#   geom_smooth(method = "lm") 

# linear model for imputing population served from service connections.
# Only train on population served not in 0:n_max (nonsensical)
jm <- j %>% filter(! population_served_count %in% 0:n_max)

# simple linear model for imputing service connection count and b1 slope
m  <- lm(population_served_count ~ service_connections_count, data = jm)
b1 <- coefficients(m)["service_connections_count"]

# predict, & change the y-intercept to 0 to avoid negative pop
j <- j %>%
  mutate(
    population_served_count = ifelse(
      population_served_count %in% 0:10,
      ceiling(service_connections_count * b1),
      population_served_count)
  )
cat("Mean imputed population served count.\n")



# recalculate area, radius for multipolygon pwsids in labeled data --------

# labeled boundaries - remove NA pwsid
wsb_labeled <- st_read(path(staging_path, "wsb_labeled.geojson")) %>% 
  filter(!is.na(pwsid))

# show there are multipolygon pwsids
multi <- st_drop_geometry(wsb_labeled) %>% 
  count(pwsid, sort = TRUE) %>% 
  filter(n > 1)
multi
cat("Detected", nrow(multi), "multipolygon pwsid groups.\n")

# add column indicating if multiple geometries are present
wsb_labeled <- wsb_labeled %>% 
  # label multipolygon geometries
  mutate(is_multi = ifelse(pwsid %in% multi$pwsid, TRUE, FALSE))
cat("Added `is_multi` field to wsb labeled data.\n")

# separate wsb labeled (wl) non-multi polygons 
wsb_labeled_no_multi <- wsb_labeled %>% 
  filter(is_multi == FALSE)

# for wsb labeled with multipolygon pwsids: 
# union geometries, recalculate area, centroids, radius
wsb_labeled_multi <- wsb_labeled %>% 
  # label multipolygon geometries
  mutate(is_multi = ifelse(pwsid %in% multi$pwsid, TRUE, FALSE)) %>% 
  filter(is_multi == TRUE) %>% 
  st_make_valid() %>% 
  # importantly, all calculations take place in AW epsg 
  st_transform(epsg_aw) %>% 
  group_by(pwsid) %>% 
  summarise(
    # combine all fragmented geometries into multipolygons
    geometry     = st_union(geometry),
    # new area is the sum of the area of all polygons
    st_areashape = sum(st_areashape),
    area_hull    = sum(area_hull),
    # new radius is calculated from the new area
    radius       = sqrt(area_hull/pi),
    # new centroids are calculated from the new geometries - bear in mind
    # that when multipolygons are separated by space, these are suspect
    centroid_x   = st_coordinates(st_geometry(st_centroid(geometry)))[, 1],
    centroid_y   = st_coordinates(st_geometry(st_centroid(geometry)))[, 2]
  ) %>% 
  ungroup() %>% 
  # convert back to the project standard epsg
  st_transform(epsg)
cat("Recalculated area, radius, centroids for multipolygon pwsids.\n")

# view
# mapview::mapview(wsb_labeled_multi, zcol = "pwsid", burst = TRUE)

# overwrite/combine labeled data with corrected multipolygon pwsids
wsb_labeled_clean <- bind_rows(wsb_labeled_no_multi, wsb_labeled_multi) 
cat("Joined multipolygon and no multi-polygon data into one object.\n")

# verify that there is only one pwsid per geometry
n <- wsb_labeled_clean %>% 
  st_drop_geometry() %>% 
  count(pwsid) %>% 
  filter(n > 1) %>% 
  nrow()
cat(n, "duplicate pwsid in labeled data following multipolygon fix.\n")

# write to staging path
st_write(wsb_labeled_clean, path(staging_path, "wsb_labeled_clean.geojson"))
cat("Wrote clean labeled data to staging path.\n")

# rm geometry and other unnecessary (for model) cols from clean wsb labels
vars_keep <- c("pwsid", "radius")

wsb_labeled_clean_df <- wsb_labeled_clean %>% 
  select(all_of(vars_keep)) %>% 
  st_drop_geometry() 


# join clean wsb labeled data to matched output and write -----------------

# add other data, including SDWIS

# cols to keep from sdwis data
cols_keep <- c("pwsid", "is_wholesaler_ind", 
               "primacy_type", "primary_source_code")

# read sdwis data and only keep the specified columns
sdwis <- path(staging_path, "sdwis_water_system.csv") %>%
  read_csv(col_select = all_of(cols_keep))

# ensure non-duplicate pwsid in SDIWS pre-join
cat("Detected", length(unique(sdwis$pwsid)), "unique pwsids", "and", 
    nrow(sdwis), "rows in SDWIS. Numbers must equal for safe join.\n")

# join to matched output, and lose 378/13435 (2.8% of labeled data) which
# is not in combined_output.csv
d <- j %>% 
  left_join(wsb_labeled_clean_df, by = "pwsid") %>% 
  left_join(sdwis)
cat("Joined matched output, labeled data, and sdwis data.\n")

# sanity row count equivalence pre and post join (this is FALSE when, for 
# instance, duplicate pwsid are present)
cat("Row count equivalence pre and post-join is", nrow(d) == nrow(j), "\n")

# write for modeling
write_csv(d, path(staging_path, "matched_output_clean.csv"))
cat("Wrote clean preprocessed data for modeling to staging path.\n")
