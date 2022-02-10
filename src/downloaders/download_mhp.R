# Download mobile home parks point data -----------------------------------

library(fs)

# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# Allow for longer timeout to map download file
options(timeout = 10000)

# Data Source: MPH ArcGIS geojson water system boundary
mhp_url <- paste0("https://opendata.arcgis.com/datasets/",
                  "4cdbccc5c538452aa91ceee277c460f9_0.geojson")

# create dir to store file and download
dir_create(path(data_path, "boundary/mhp"))
download.file(mhp_url, path(data_path, "/boundary/mhp/mhp.geojson"))
cat("Downloaded mobile home park point data.\n")
