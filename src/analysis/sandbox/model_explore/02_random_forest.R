# fit a random forest -----------------------------------------------------

library(tidyverse)
library(tidymodels)
library(sf)
library(fs)
library(vip)

staging_path <- Sys.getenv("WSB_STAGING_PATH")

# read full dataset 
d <- read_csv(path(staging_path, "matched_output_clean.csv")) 

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

# model and workflow
rf_mod <- 
  rand_forest(trees = 1000) %>% 
  set_engine("ranger", importance = "impurity") %>% 
  set_mode("regression")

rf_wflow <- 
  workflow() %>% 
  add_formula(
    radius ~ 
      population_served_count + 
      # importantly, the RF can have correlated predictors, so we add
      # service connections, and don't need to account for interactions
      service_connections_count + 
      # use the cleaned owner type code from preprocess.R, which converts 
      # 2 "N" owner type codes to "M" so that models can evaluate
      owner_type_code_clean + 
      is_wholesaler_ind + 
      satc
  ) %>% 
  add_model(rf_mod) 

# fit the random forest model
rf_fit <- fit(rf_wflow, train)

# show variable importance
rf_fit %>%
  extract_fit_parsnip() %>%
  vip(geom = "point")

# predict on test set
rf_test_res <- test %>% 
  # select(radius) %>% 
  bind_cols(predict(rf_fit, test)) 

# plot residuals
rf_test_res %>% 
  ggplot(aes(log10(radius), log10(.pred), color = owner_type_code)) + 
  geom_point(alpha = 0.4) + 
  geom_abline(lty = 2, color = "red") + 
  labs(y = "Predicted radius (log10)", x = "Radius (log10)") +
  # scale and size the x- and y-axis uniformly
  coord_obs_pred()

# RMSE
rf_metrics <- metric_set(rmse, rsq, mae)
rf_metrics(rf_test_res, truth = log10(radius), estimate = log10(.pred))
