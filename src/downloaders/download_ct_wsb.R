# Download CT water system data -------------------------------------------

library(fs)

# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# Allow for longer timeout to map download file
options(timeout = 10000)

# Data Source: Connecticut ArcGIS geojson water system boundary
ct_url <- paste0("https://github.com/NIEPS-Water-Program/",
                 "water-affordability/raw/main/data/ct_systems.geojson")

# create dir to store file and download
dir_create(path(data_path, "boundary/ct"))
download.file(ct_url, path(data_path, "boundary/ct/ct.geojson"))
cat("Downloaded CT polygon boundary data.\n")
