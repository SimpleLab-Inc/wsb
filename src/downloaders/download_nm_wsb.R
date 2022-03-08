# Download NM water system data -------------------------------------------

library(fs)

# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# Allow for longer timeout to map download file
options(timeout = 10000)

# Data Source: New Mexico ArcGIS geojson water system boundary
nm_url <- paste0("https://github.com/NIEPS-Water-Program/",
                 "water-affordability/raw/main/data/nm_systems.geojson")

# create dir to store file and download
dir_create(path(data_path, "boundary/nm"))
download.file(nm_url, path(data_path, "boundary/nm/nm.geojson"))
cat("Downloaded NM polygon boundary data.\n")
