# Download MO water service boundaries ------------------------------------

library(fs)

# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# Allow for longer timeout to map download file
options(timeout = 10000)

# Data Source: Missouri ArcGIS geojson water system boundary
url <- paste0("https://opendata.arcgis.com/datasets/",
                 "c3bee75a86e04856b28d7f1ce2a24e6f_0.geojson")

# create dir to store file and download
dir_create(path(data_path, "boundary/mo"))
download.file(url, path(data_path, "boundary/mo/mo.geojson"))
cat("Downloaded MO polygon boundary data.\n")
