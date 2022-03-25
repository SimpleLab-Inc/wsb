# fit a random forest -----------------------------------------------------

library(tidyverse)
library(tidymodels)
library(sf)
library(fs)
library(vip)

staging_path <- Sys.getenv("WSB_STAGING_PATH")
epsg_aw      <- Sys.getenv("WSB_EPSG_AW")
epsg         <- as.numeric(Sys.getenv("WSB_EPSG"))

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
xgb_mod <- 
  boost_tree(
    trees = 1000,
    tree_depth = tune(), 
    min_n = tune(), 
    loss_reduction = tune(),                     
    sample_size = tune(),
    mtry = tune(),    
    learn_rate = tune()
  ) %>% 
  set_engine("xgboost") %>% 
  set_mode("regression")

# hyperparameter space
xgb_grid <- grid_latin_hypercube(
  tree_depth(),
  min_n(),
  loss_reduction(),
  sample_size = sample_prop(),
  finalize(mtry(), train),
  learn_rate(),
  size = 30
)

xgb_wflow <- 
  workflow() %>% 
  add_formula(
    radius ~ 
      population_served_count + 
      # importantly, the RF can have correlated predictors, so we add
      # service connections, and don't need to account for interactions
      service_connections_count + 
      owner_type_code + 
      is_wholesaler_ind + 
      satc
  ) %>% 
  add_model(xgb_mod) 

# CV
set.seed(123)
xgb_folds <- vfold_cv(train, strata = radius)

# tune the model
doParallel::registerDoParallel()

set.seed(234)
xgb_res <- tune_grid(
  xgb_wflow,
  resamples = xgb_folds,
  grid = xgb_grid,
  control = control_grid(save_pred = TRUE)
)

# visualize model performance across tuning grid
xgb_res %>%
  collect_metrics() %>%
  filter(.metric == "rsq") %>%
  select(mean, mtry:sample_size) %>%
  pivot_longer(mtry:sample_size,
               values_to = "value",
               names_to = "parameter"
  ) %>%
  ggplot(aes(value, mean, color = parameter)) +
  geom_point(alpha = 0.8, show.legend = FALSE) +
  facet_wrap(~parameter, scales = "free_x") +
  labs(x = NULL, y = "rsq")

show_best(xgb_res, "rsq")

# select best model
final_xgb <- finalize_workflow(
  xgb_wflow, select_best(xgb_res, "rsq")
)

final_xgb

# fit the final xgboost model on training data
xgb_fit <- fit(final_xgb, train)

# show variable importance
xgb_fit %>%
  extract_fit_parsnip() %>%
  vip(geom = "point")

# predict on test set
xgb_test_res <- test %>% 
  select(radius) %>% 
  bind_cols(predict(xgb_fit, test)) 

# plot residuals
xgb_test_res %>% 
  ggplot(aes(log10(radius), .pred)) + 
  geom_point(alpha = 0.4) + 
  geom_abline(lty = 2, color = "red") + 
  labs(y = "Predicted radius (log10)", x = "Radius (log10)") +
  # scale and size the x- and y-axis uniformly
  coord_obs_pred()

# RMSE
xgb_metrics <- metric_set(rmse, rsq, mae)
xgb_metrics(xgb_test_res, truth = log10(radius), estimate = log10(.pred))
