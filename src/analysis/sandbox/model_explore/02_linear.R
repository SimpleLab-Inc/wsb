# linear model ------------------------------------------------------------

# SWDIS water_system.csv continuous vars:
#   - population_served_count: rescale, likely to have high leverage
#   - service_connections_count
#   - we have zip code: perhaps we use this to pull census vars
#     or other vars like road density, population density, but we
#     are unsure of data quality of zip

# SDWIS water_system.csv categorical vars:
#   - is_wholesaler_ind: complete and can use
#   - primacy_type (state, territory, tribal): can't use because only 
#     "state" observations have labeled radii (not territory or tribal)
#   - primary_source_code: SW, GW, etc.

library(tidyverse)
library(tidymodels)
library(sf)
library(fs)

staging_path <- Sys.getenv("WSB_STAGING_PATH")
epsg_aw      <- Sys.getenv("WSB_EPSG_AW")
epsg         <- as.numeric(Sys.getenv("WSB_EPSG"))

# read dataset and log10 transform the response - only for linear model
d <- read_csv(path(staging_path, "matched_output_clean.csv")) %>% 
  mutate(radius = log10(radius),
         density = population_served_count * service_connections_count)

# unlabeled data (du) and labeled data (dl)
du <- d %>% filter(is.na(radius))
dl <- d %>% filter(!is.na(radius))

# plit labeled data (dl) into train and test with stratified random sampling
# in each of the radius quartiles to account for the lognormal distribution
# of the response variable (radius) and avoid overfitting to small radius obs
set.seed(55)
dl_split <- initial_split(dl, prop = 0.8, strata = radius)
train    <- training(dl_split) 
test     <- testing(dl_split)

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

# predict on the test set and bind mean predictions and CIs
lm_test_res <- test %>% 
  select(radius) %>% 
  bind_cols(predict(lm_fit, test)) %>% 
  bind_cols(predict(lm_fit, test, type = "conf_int"))

# plot residuals
lm_test_res %>% 
  ggplot(aes(radius, .pred)) + 
  geom_point(alpha = 0.4) + 
  geom_abline(lty = 2, color = "red") + 
  labs(y = "Predicted radius (log10)", x = "Radius (log10)") +
  # scale and size the x- and y-axis uniformly
  coord_obs_pred()

# RMSE
lm_metrics <- metric_set(rmse, rsq, mae)
lm_metrics(lm_test_res, truth = radius, estimate = .pred)
