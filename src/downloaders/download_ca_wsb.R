# Download CA water system data -------------------------------------------

library(fs)

# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# Allow for longer timeout to map download file
options(timeout = 10000)

# Data Source: California ArcGIS geojson water system boundary
ca_url <- paste0("https://github.com/NIEPS-Water-Program/",
                 "water-affordability/raw/main/data/ca_systems.geojson")

# create dir to store file and download
dir_create(path(data_path, "boundary/ca"))
download.file(ca_url, path(data_path, "boundary/ca/ca.geojson"))
cat("Downloaded CA polygon boundary data.\n")
