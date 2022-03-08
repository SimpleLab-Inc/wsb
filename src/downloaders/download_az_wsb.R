# Download AZ water system data -------------------------------------------

library(fs)

# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# Allow for longer timeout to map download file
options(timeout = 10000)

# Data Source: Arizona ArcGIS geojson water system boundary
url <- paste0("https://opendata.arcgis.com/datasets/",
              "9992e59e46bb466584f9694f897f350a_0.geojson")

# create dir to store file and download
dir_create(path(data_path, "boundary/az"))
download.file(url, path(data_path, "boundary/az/az.geojson"))
cat("Downloaded AZ polygon boundary data.\n")
