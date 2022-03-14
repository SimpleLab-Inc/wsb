# Download NJ water system data -------------------------------------------

library(fs)

# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# Allow for longer timeout to map download file
options(timeout = 10000)

# Data Source: New Jersey ArcGIS geojson water system boundary
url <- paste0("https://opendata.arcgis.com/datasets/",
                 "00e7ff046ddb4302abe7b49b2ddee07e_13.geojson")

# create dir to store file and download
dir_create(path(data_path, "boundary/nj"))
download.file(url, path(data_path, "boundary/nj/nj.geojson"))
cat("Downloaded NJ polygon boundary data.\n")
