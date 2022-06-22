# preprocess data for model -----------------------------------------------

library(tidyverse)
library(sf)
library(fs)
library(RPostgres)

staging_path <- Sys.getenv("WSB_STAGING_PATH")

# Parse the conn string and open a DB connection
conn_str <- Sys.getenv("POSTGIS_CONN_STR")
matches <- str_match(conn_str,
                     "postgresql://(\\w+):(\\w+)@(\\w+):(\\d+)/(\\w+)")[,2:6]

conn = dbConnect(
  RPostgres::Postgres(),
  host     = matches[3],
  dbname   = matches[5],
  user     = matches[1],
  password = matches[2],
  port     = matches[4]
)

# this is the critical service connection count below which (inclusive) we
# assume that the value is nonsensical, and impute it based on population. 
# We also assume that population counts less than 25 are unreasonable, 
# and only work with populations >= 25 (CWS definition)
n_max_sc  <- 15
n_max_pop <- 25
cat("\n\nPreparing to mean impute service connection count", 
    "for all values >=", n_max_sc, ".\n")

# regex to catch all states, DC, and all numeric tribal primacy agencies
rx <- paste0(paste(c(state.abb, "DC"), collapse = "|"), "|", "^[0-9]")

# The "masters" contain the best data from sdwis, ucmr, mhp, etc.
pws = dbGetQuery(conn,"
  SELECT
    pwsid, is_wholesaler_ind, primacy_type, primary_source_code,
    service_connections_count, population_served_count, primacy_agency_code,
    owner_type_code, service_area_type_code, geometry_lat, geometry_long
  FROM pws_contributors
  WHERE source_system = 'master';")

# j stands for joined data, read and rm rownumber column, then drop
# observations without a centroid or with nonsensical service connections
j <- pws %>% 
  filter(!is.na(geometry_lat) | !is.na(geometry_long)) %>% 
  # filter to CWS and assume each connection must serve at least 1 person
  filter(service_connections_count >= n_max_sc,
         population_served_count   >= n_max_pop) %>% 
  # remove rows not in contiguous US, mostly Puerto Rico
  filter(str_detect(primacy_agency_code, rx))

cat("Read", nrow(j), "matched outputs with >=", 
    n_max_sc, "connections and >=", n_max_pop, 
    "population count in the 50 states and DC.\n")


# mean impute service connections == 0 with linear model ------------------

# A 2022-03-08 meeting with IoW/BC/EPIC recommended filtering out 
# wholesalers and water systems with a zero population count. However, 
# many water systems have service connection counts (e.g., between 0 and 10), 
# but very high population (e.g., in the hundreds to thousands), wholesalers 
# in labeled data are primarily found in WA and TX, and wholesalers 
# typically occupy urban areas and do not contain smaller pwsids. Thus, we 
# retain all observations and mean impute suspect (between 0 and N) service
# connections.

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
# Only train on service connections and population served >= n_max_sc
# and n_max_pop for CWS 
jm <- j %>% filter(service_connections_count >= n_max_sc,
                   population_served_count   >= n_max_pop)

# simple linear model for imputing service connection count and b1 slope
m  <- lm(service_connections_count ~ population_served_count, data = jm)
b1 <- coefficients(m)["population_served_count"]

# predict, & change the y-intercept to 0 to avoid negative connections
j <- j %>%
  mutate(
    service_connections_count = ifelse(
      service_connections_count < n_max_sc,
      ceiling(population_served_count * b1),
      service_connections_count)
  )
cat("Mean imputed service connection count.\n")


# read labeled data with recalculated area, centroid for multipolygon pwsids --

# read wsb_labeled_clean
wsb_labeled_clean <- path(staging_path, "wsb_labeled_clean.geojson") %>% 
  st_read(quiet = TRUE) 

# rm geometry and other unnecessary (for model) cols from clean wsb labels
vars_keep <- c("pwsid", "radius")

wsb_labeled_clean_df <- wsb_labeled_clean %>% 
  select(all_of(vars_keep)) %>% 
  st_drop_geometry() 


# Combine pws data with labeled data (radiuses) -----------------

d <- j %>% 
  left_join(wsb_labeled_clean_df, by = "pwsid")

cat("Joined pws data and labeled data.\n")

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
    satc = fct_lump_n(satc, 3), 
    satc = as.character(satc), 
    satc = ifelse(is.na(satc), "Other", satc),
    # convert T/F is_wholesaler_ind to character for dummy var prep
    is_wholesaler_ind = ifelse(is_wholesaler_ind == TRUE, 
                               "wholesaler", "not wholesaler"),
    # there are only 2 "N" owner type codes in Tier 1 data, which makes
    # this parameter impossible to fit via models, so coerce them to "M"
    # and remove this when we have more Tier 1 "N" data
    owner_type_code_clean = ifelse(owner_type_code == "N",
                                   "M", owner_type_code)
  )
cat("Cleaned data according to EDA-generated insights.\n")

# write for modeling
write_csv(d, path(staging_path, "model_input_clean.csv"))
cat("Wrote clean preprocessed data for modeling to staging path.\n")
