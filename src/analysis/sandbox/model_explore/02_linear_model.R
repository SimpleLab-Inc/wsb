# space to explore candidate models, characterize error, select features, and so on

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

# read full dataset 
d <- read_csv(path(staging_path, "matched_output_clean.csv")) %>% 
  # cleaning informed by EDA
  mutate(
    # when radius == 0, make it NA
    radius = ifelse(radius == 0, NA, radius),
    # convert units from meters to km and log10 transform
    radius = log10(radius/1000),
    # convert predictors to log10
    # population_served_count   = log10(population_served_count),
    # service_connections_count = log10(service_connections_count),
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
                               "wholesaler", "not wholesaler")
  )

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
  recipe(
    radius ~ 
      population_served_count + owner_type_code + is_wholesaler_ind + satc,
    data = train
  ) %>% 
  # convert predictors to log10
  step_log(population_served_count, base = 10) %>% 
  # encode categorical variables  
  step_dummy(all_nominal_predictors()) %>% 
  # set interaction effects
  step_interact(~population_served_count:starts_with("owner_type_code")) %>%
  step_interact(~population_served_count:starts_with("is_wholesaler_ind")) %>%
  step_interact(~population_served_count:starts_with("satc"))

# specify model and engine for linear model and rf
lm_mod <- linear_reg() %>% set_engine("lm")

# lm workflow
lm_wflow <- 
  workflow() %>% 
  add_model(lm_mod) %>% 
  add_recipe(lm_recipe)

# fit the linear model
lm_fit <- fit(lm_wflow, train)





# fit a random forest model
# rf_fit <- rf_mod %>% 
#   fit(
#     radius ~ population_served_count + 
#       service_connections_count + 
#       is_wholesaler_ind, 
#     data = train
#   )

# sanity check diagnostic plots
# lm_fit %>% extract_fit_engine() %>% plot()
tidy(lm_fit)
# rf_fit %>% extract_fit_engine()

# predict on test set
test %>% 
  bind_cols(predict(lm_fit, test)) %>% 
  bind_cols(predict(lm_fit, test, type = "conf_int"))

du %>% 
  bind_cols(mean_pred) %>% 
  bind_cols(conf_int_pred) %>% 
  ggplot(aes(x = cyl)) +
  geom_point(aes(y = .pred)) +
  geom_errorbar(aes(ymin = .pred_lower, 
                    ymax = .pred_upper),
                width = 0.2) +
  labs(y = "wt")





# formula sets
# formulas <- list(
#   combined =
#     radius ~ (population_served_count + service_connections_count)^2 +
#       is_wholesaler_ind,
#   separate =
#     radius ~ population_served_count + service_connections_count +
#       is_wholesaler_ind
# )


# rf_mod <- rand_forest(trees = 500) %>% 
#   set_engine("ranger") %>% 
#   set_mode("regression")

# multiple workflows
# radius_models <- workflow_set(
#   preproc = formulas, 
#   models  = list(lm = lm_mod, rf_mod)
# )

# fit models
# radius_models <- radius_models %>%
#   mutate(fit = map(info, ~fit(.x$workflow[[1]], train)))