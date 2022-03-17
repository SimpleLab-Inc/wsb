# fit a random forest -----------------------------------------------------

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
  set_engine("ranger") %>% 
  set_mode("regression")

rf_wflow <- 
  workflow() %>% 
  add_formula(
    radius ~ 
      population_served_count + 
      service_connections_count + 
      owner_type_code + 
      is_wholesaler_ind + 
      satc
  ) %>% 
  add_model(rf_mod) 

# fit the random forest model
rf_fit <- rf_wflow %>% fit(data = ames_train)


# sanity check diagnostic plots
# lm_fit %>% extract_fit_engine() %>% plot()
tidy(lm_fit)
# rf_fit %>% extract_fit_engine()

# predict on test set
test %>% 
  select(radius) %>% 
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

