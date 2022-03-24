# Download CT water system data -------------------------------------------

source(here::here("src/downloaders/states/download_state_helpers.R"))

# Data Source: Connecticut ArcGIS shapefile water system boundary
url <- paste0("https://portal.ct.gov/-/media/Departments-and-Agencies/",
              "DPH/dph/drinking_water/GIS/",
              "Buffered_Community_PWS_Service_Areas.zip")

download_wsb(url, "ct")
