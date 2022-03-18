# Download AR water system data -------------------------------------------

library(fs)

# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# Allow for longer timeout to map download file
options(timeout = 10000)

# Data Source: Arkansas ArcGIS shapefile water system boundary
url <- paste0("https://geostor-vectors.s3.amazonaws.com/Utilities/SHP/",
              "PUBLIC_WATER_SYSTEMS.zip")

# create dir to store folder and download
dir_path <- path(data_path, "boundary/ar")
file_path <- path(dir_path, "ar.zip")
dir_create(dir_path)
download.file(url, file_path)
cat("Downloaded AR polygon boundary data.\n")

# unzip folder
unzip(zipfile=file_path, exdir=dir_path)
