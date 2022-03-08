# Download KS water system data -------------------------------------------

library(fs)

# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# Allow for longer timeout to map download file
options(timeout = 10000)

# Data Source: Kansas ArcGIS geojson water system boundary
ks_url <- paste0("https://github.com/NIEPS-Water-Program/",
                 "water-affordability/raw/main/data/ks_systems.geojson")

# create dir to store file and download
dir_create(path(data_path, "boundary/ks"))
download.file(ks_url, path(data_path, "boundary/ks/ks.geojson"))
cat("Downloaded KS polygon boundary data.\n")
