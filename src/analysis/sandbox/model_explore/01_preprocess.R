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
  filter(population_served_count > 0) 
cat("Read", nrow(j), 
    "matched outputs with nonzero service connection count.\n")


# mean impute service connections == 0 with linear model ------------------

# A 2022-03-08 meeting with IoW/BC/EPIC recommended filtering out 
# wholesalers and water systems with a zero population count. However, 
# many water systems have service connection counts (e.g., between 0 and 10), 
# but very high population (e.g., in the hundreds to thousands), wholesalers 
# in labeled data are primarily found in WA and TX, and wholesalers 
# typically occupy urban areas and do not contain smaller pwsids. Thus, we 
# retain all observations and mean impute suspect (between 0 and N) service
# connections.

# this is the critical service connection count below which (inclusive) we
# assume that the value is nonsensical, and impute it based on population
n_max <- 15
cat("Preparing to mean impute service connection count", 
    "for all values >=", n_max, ".\n")

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

# linear model for imputing service connections from population served
# Only train on population served >= n_max (community water systems)
jm <- j %>% filter(service_connections_count >= n_max)

# simple linear model for imputing service connection count and b1 slope
m  <- lm(service_connections_count ~ population_served_count, data = jm)
b1 <- coefficients(m)["population_served_count"]

# predict, & change the y-intercept to 0 to avoid negative connections
j <- j %>%
  mutate(
    service_connections_count = ifelse(
      service_connections_count %in% 0:10,
      ceiling(population_served_count * b1),
      service_connections_count)
  )
cat("Mean imputed service connection count.\n")


# read labeled data with recalculated area, centroid for multipolygon pwsids --

# read wsb_labeled_clean
wsb_labeled_clean <- st_read(path(staging_path, "wsb_labeled_clean.geojson")) 

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


# apply cleaning informed by EDA ------------------------------------------

d <- d %>% 
  mutate(
    # when radius == 0, make it NA
    radius = ifelse(radius == 0, NA, radius),
    # split type codes in the "python list" into chr vectors
    satc = strsplit(service_area_type_code, ", "),
    # map over the list to remove brackets ([]) and quotes (')
    satc = map(satc, ~str_remove_all(.x, "\\[|\\]|'")),
    # sort the resulting chr vector
    satc = map(satc, ~sort(.x)), 
    # collapse the sorted chr vector
    satc = map_chr(satc, ~paste(.x, collapse = "")),
    # convert the sorted chr vector to factor with reasonable level count
    satc = fct_lump_prop(satc, 0.02), 
    satc = as.character(satc), 
    satc = ifelse(is.na(satc), "Other", satc),
    # convert T/F is_wholesaler_ind to character for dummy var prep
    is_wholesaler_ind = ifelse(is_wholesaler_ind == TRUE, 
                               "wholesaler", "not wholesaler"),
    # make native american owner types (only 2 present) public/private (M)
    owner_type_code = ifelse(owner_type_code == "N", "M", owner_type_code)
  )
cat("Cleaned data according to EDA-generated insights.\n")

# write for modeling
write_csv(d, path(staging_path, "matched_output_clean.csv"))
cat("Wrote clean preprocessed data for modeling to staging path.\n")
