# preprocessing for model -------------------------------------------------

library(tidyverse)
library(tidymodels)
library(sf)
library(fs)

# data input location for modeling is the post-transformer staging path
staging_path <- Sys.getenv("WSB_STAGING_PATH")

# j stands for joined data, read and rm rownumber column, then drop
# observations without a centroid or with nonsensical service connections
j <- read_csv(path(staging_path, "matched_output.csv"), col_select = -1) %>% 
  filter(!is.na(echo_latitude) | !is.na(echo_longitude)) %>% 
  # we also filter out 0 service connection count systems - 267 (0.4%), 
  # this should be cleaned/imputed in the transformer
  filter(service_connections_count > 0) 


# mean impute population_served == 0 with linear model --------------------

# A 2022-03-08 meeting with IoW/BC/EPIC recommended filtering out water   
# systems with a zero population count, however, many water systems have
# low population counts (e.g., between 0 and 10), but very high service
# connection count (e.g., in the hundreds to thousands). Thus, we retain 
# all observations and mean impute nonsensical (between 0 and N) 
# population served values.

# this is the critical population served count below which (inclusive) we
# assume that the value is nonsensical, and impute it based on the service
# connection count, which tends to be present and more correct.
n_max <- 10

# we learned in the Feb 2022 EDA (sandbox/eda/eda_february.Rmd) that
# population served and service connection count had outliers that were 
# likely incorrect. Here we highlight "bad" high leverage points
j %>%
  mutate(
    grp = ifelse(
      population_served_count %in% 0:n_max, "bad", "good"
    )
  ) %>%
  ggplot(aes(service_connections_count, population_served_count)) +
  geom_point(aes(color = grp), alpha = 0.5) +
  geom_smooth(method = "lm")

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


# add dependent variable (radius) to data ---------------------------------

# labeled boundaries
wsb_labeled <- st_read(path(staging_path, "wsb_labeled.geojson")) %>% 
  # select important features for model
  select(pwsid, radius, centroid_x, centroid_y) %>% 
  st_drop_geometry()

# join to matched output, and lose 378/13435 (2.8% of labeled data) which
# is not in combined_output.csv
j <- j %>% left_join(wsb_labeled, by = "pwsid")

# write for modeling
write_csv(j, path(staging_path, "matched_output_clean.csv"))
