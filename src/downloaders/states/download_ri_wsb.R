# Download RI water system data -------------------------------------------
library(geojsonsf)
library(fs)
library(sf)
library(urltools)

# Path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# Data Source: Arkansas ArcGIS shapefile water system boundary
url <- paste0("https://risegis.ri.gov/hosting/rest/services/RIDEM/RI_DrinkingWater_ServiceAreas/",
              "FeatureServer/1/query?where=1%3D1&outFields=*&f=geojson")

# Use geojson reader for ESRI Rest end points to get data
ri <- geojson_sf(url)

# Create outputted file directory
dir_path <- paste0(data_path, "/boundary/ri")
dir_create(dir_path) 

# Write RI geojson
path_out <- paste0(dir_path, "/ri.geojson")
if(file_exists(path_out)) file_delete(path_out)

st_write(ri, path_out)


