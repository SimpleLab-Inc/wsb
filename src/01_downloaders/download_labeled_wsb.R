# Download water system data

# Setup  -----------------------------------------------------------------------

library(tidyverse)
library(here)
library(fs)
library(glue)


# Allow for longer timeout to map download files
options(timeout = 10000)

# Download ---------------------------------------------------------------------

# Data Source: Internet of Water 
## 10 geojson water system boundaries from Internet of Water repository
base_url <- paste0("https://github.com/NIEPS-Water-Program/",
                   "water-affordability/raw/main/data/")
states <- c("ca", "ct", "ks", "nc", "nj", "nm", "or", "pa", "tx", "wa")
urls <- paste0(base_url, states, "_systems.geojson")

map2(urls, states,
     ~download.file(.x, here("data/boundary", .y, glue("{.y}.geojson"))))
