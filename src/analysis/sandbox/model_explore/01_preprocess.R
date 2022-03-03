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

# we learned in the EDA Feb deliverable sandbox/eda/eda_february.Rmd that 
# population served and service connection count had outliers that were likely
# incorrect. This should eventually be moved to the transformer.
j %>%
  mutate(grp = ifelse(population_served_count %in% 0:10, "bad", "good")) %>% 
  ggplot(aes(service_connections_count, population_served_count)) + 
  geom_point(aes(color = grp), alpha = 0.5) + 
  geom_smooth(method = "lm")

# linear model for imputing population served from service connections.
# Only train on population served not in 0:10 (nonsensical)
jm <- j %>% filter(! population_served_count %in% 0:10)

# simple linear model for imputing service connection count
m  <- lm(population_served_count ~ service_connections_count, data = jm)
b1 <- coefficients(m)["service_connections_count"]

# predict, and artificially inflate the intercept to 0 to avoid negative pop
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
