# Download labeled water system data --------------------------------------

library(fs)
library(tidyverse)
library(glue)

# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# Allow for longer timeout to map download files
options(timeout = 10000)

# Data Source: Internet of Water 
## 10 geojson water system boundaries from Internet of Water repository
base_url <- paste0("https://github.com/NIEPS-Water-Program/",
                   "water-affordability/raw/main/data/")
states <- c("ca", "ct", "ks", "nc", "nj", "nm", "or", "pa", "tx", "wa")
urls <- paste0(base_url, states, "_systems.geojson")

dir_create(path(data_path, "boundary", states))
map2(urls, states,
     ~download.file(.x, path(data_path, "boundary", .y, glue("{.y}.geojson"))))
cat("Downloaded data for:", states, "\n")
