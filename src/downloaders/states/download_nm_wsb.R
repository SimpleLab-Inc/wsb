# Download NM water system data -------------------------------------------

source(here::here("src/downloaders/states/download_state_helpers.R"))

# Data Source: New Mexico ArcGIS geojson water system boundary
url <- paste0("https://catalog.newmexicowaterdata.org/dataset/",
              "5d069bbb-1bfe-4c83-bbf7-3582a42fce6e/resource/",
              "ccb9f5ce-aed4-4896-a2f1-aba39953e7bb/download/pws_nm.geojson")

download_wsb(url, "nm")
