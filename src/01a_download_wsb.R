# download water system data

library(tidyverse)
library(here)
library(fs)
library(glue)

# allow for longer timeout to map download files
options(timeout = 10000)

# download geojson water system boundaries from IoW -----------------------
base_url <- paste0("https://github.com/NIEPS-Water-Program/",
                   "water-affordability/raw/main/data/")
states <- c("ca", "ct", "ks", "nc", "nj", "nm", "or", "pa", "tx", "wa")
urls <- paste0(base_url, states, "_systems.geojson")

map2(urls, states,
     ~download.file(.x, here("data/boundary", .y, glue("{.y}.geojson"))))


# download FRS centroids --------------------------------------------------





# download SDWIS admin data -----------------------------------------------



