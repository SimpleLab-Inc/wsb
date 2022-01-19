# transform water system data to standard model

library(tidyverse)
library(here)
library(fs)
library(sf)

# projected metric coordinate reference system for calculations
epsg <- 3310

# make valid ST
