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

# model reproducibility 
set.seed(55)

# full dataset
d <- read_csv(path(staging_path, "matched_output_clean.csv"))

# labeled data (dl): split into train and test with stratified random sampling
# in each of the radius quartiles to account for the lognormal distribution
# of the response variable (radius) and avoid overfitting to small radius obs
dl      <- d %>% filter(!is.na(radius))
d_split <- initial_split(dl, prop = 0.8, strata = radius)
train   <- training(d_split)
test    <- testing(d_split)

# unlabeled data
du <- d %>% filter(is.na(radius))

# specify model and engine 
lm_mod <- linear_reg() %>% 
  set_engine("lm")

# fit the model
lm_fit <- lm_mod %>% 
  # consider interaction effect between pop and connections because they 
  # are highly correlated ~ 0.83 via cor.test()
  fit(radius ~ (population_served_count + service_connections_count)^2, 
      data = train)

lm_fit
tidy(lm_fit)

# predict
mean_pred <- predict(lm_fit, du)
conf_int_pred <- predict(lm_fit, du, type = "conf_int")


du %>% 
  bind_cols(mean_pred) %>% 
  bind_cols(conf_int_pred) %>% 
  ggplot(aes(x = cyl)) +
  geom_point(aes(y = .pred)) +
  geom_errorbar(aes(ymin = .pred_lower, 
                    ymax = .pred_upper),
                width = 0.2) +
  labs(y = "wt")