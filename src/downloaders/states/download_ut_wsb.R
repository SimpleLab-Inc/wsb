# Download UT water system data -------------------------------------------

source(here::here("src/downloaders/states/download_state_helpers.R"))

# Data Source: Utah ArcGIS geojson water system boundary
url <- paste0("https://services.arcgis.com/ZzrwjTRez6FJiOq4/arcgis/rest/",
              "services/CulinaryWaterServiceAreas/FeatureServer/0/",
              "query?outFields=*&where=1%3D1&f=geojson")

download_wsb(url, "ut", "geojson")
