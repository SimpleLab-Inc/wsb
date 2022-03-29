# linear model ------------------------------------------------------------

library(tidyverse)
library(tidymodels)
library(sf)
library(fs)

staging_path <- Sys.getenv("WSB_STAGING_PATH")
epsg         <- as.numeric(Sys.getenv("WSB_EPSG"))

# read dataset and log transform the response - only for linear model
d <- read_csv(path(staging_path, "matched_output_clean.csv")) %>% 
  mutate(radius  = log10(radius),
         # multiply correlated predictors
         density = population_served_count * service_connections_count)

cat("\n\nRead `matched_output_clean.csv` from preprocess script.\n")

# unlabeled data (du) and labeled data (dl)
du <- d %>% filter(is.na(radius))
dl <- d %>% filter(!is.na(radius))

# split labeled data (dl) into train and test with stratified random sampling
# in each of the radius quartiles to account for the lognormal distribution
# of the response variable (radius) and avoid overfitting to small radius obs
set.seed(55)
dl_split <- initial_split(dl, prop = 0.8, strata = radius)
train    <- training(dl_split) 
test     <- testing(dl_split)

cat("Split data into train and test sets.\n")

# lm recipe
lm_recipe <- 
  # specify the model - interaction terms come later
  recipe(
    radius ~ 
      service_connections_count + 
      owner_type_code + 
      satc + 
      is_wholesaler_ind,
    data = train
  ) %>% 
  # convert predictors to log10
  step_log(service_connections_count, base = 10) %>% 
  # encode categorical variables  
  step_dummy(all_nominal_predictors()) %>% 
  # specify interaction effects
  step_interact(~service_connections_count:starts_with("owner_type_code")) %>%
  step_interact(~service_connections_count:starts_with("satc")) %>% 
  step_interact(~service_connections_count:starts_with("is_wholesaler_ind")) 

# specify model and engine for linear model and rf
lm_mod <- linear_reg() %>% set_engine("lm")

# lm workflow
lm_wflow <- 
  workflow() %>% 
  add_model(lm_mod) %>% 
  add_recipe(lm_recipe)

# fit the linear model on the training set
lm_fit <- fit(lm_wflow, train)
cat("Fit model on training set.\n")

# predict on the test set and bind mean predictions and CIs
# lm_test_res <- test %>% 
#   select(radius) %>% 
#   bind_cols(predict(lm_fit, test)) %>% 
#   bind_cols(predict(lm_fit, test, type = "conf_int"))

# plot residuals
# lm_test_res %>% 
#   ggplot(aes(radius, .pred)) + 
#   geom_point(alpha = 0.4) + 
#   geom_abline(lty = 2, color = "red") + 
#   labs(y = "Predicted radius (log10)", x = "Radius (log10)") +
#   # scale and size the x- and y-axis uniformly
#   coord_obs_pred()

# RMSE
# lm_metrics <- metric_set(rmse, rsq, mae)
# lm_metrics(lm_test_res, truth = radius, estimate = .pred)


# apply modeled radii to centroids for all data and write -----------------

# read matched output for centroid lat/lng
matched_output_clean <- path(staging_path, "matched_output_clean.csv") %>% 
  read_csv(col_select = c("pwsid", "geometry_lat", "geometry_long")) %>% 
  st_as_sf(coords = c("geometry_long", "geometry_lat"), crs = epsg) %>% 
  suppressMessages()
cat("Read labeled and unlabeled data to fit model on.\n")

# fit the model on all data, apply the spatial buffer, and write
t3m <- d %>% 
  select(pwsid, radius) %>% 
  bind_cols(predict(lm_fit, d)) %>% 
  bind_cols(predict(lm_fit, d, type = "conf_int", level = 0.95)) %>% 
  # exponentiate results back to median (unbiased), and 5/95 CIs
  mutate(across(where(is.numeric), ~10^(.x))) %>% 
  # add matched output lat/lng centroids and make spatial
  left_join(matched_output_clean, by = "pwsid") %>% 
  st_as_sf() %>% 
  # convert to projected metric CRS for accurate, efficient buffer. 
  # The project CRS (4326) is inappropriate because units are degrees.
  st_transform(3310)
cat("Fit model on all data and added 5/95 CIs.\n")

# create buffers for median, CI lower, and CI upper (5/95) predictions
# (in units meters) and then transform back into projet CRS
t3m_med <- st_buffer(t3m, t3m$.pred      ) %>% st_transform(epsg)
t3m_cil <- st_buffer(t3m, t3m$.pred_lower) %>% st_transform(epsg)
t3m_ciu <- st_buffer(t3m, t3m$.pred_upper) %>% st_transform(epsg)
cat("Created median and 5/95 CI buffers.\n")

# paths to write modeled data
path_t3m_med <- path(staging_path, "tier3_median.geojson")
path_t3m_cil <- path(staging_path, "tier3_ci_upper_95.geojson")
path_t3m_ciu <- path(staging_path, "tier3_ci_lower_05.geojson")

# write and delete layer if it already exists
st_write(t3m_med, path_t3m_med, delete_dsn = TRUE, quiet = TRUE)
st_write(t3m_cil, path_t3m_cil, delete_dsn = TRUE, quiet = TRUE)
st_write(t3m_ciu, path_t3m_ciu, delete_dsn = TRUE, quiet = TRUE)
cat("Wrote Tier 3 model putput to `WSB_STAGING_PATH`.\n")
