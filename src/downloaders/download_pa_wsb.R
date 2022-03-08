# Download PA water system data -------------------------------------------

library(fs)

# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# Allow for longer timeout to map download file
options(timeout = 10000)

# Data Source: Pennsylvania ArcGIS geojson water system boundary
pa_url <- paste0("https://github.com/NIEPS-Water-Program/",
                 "water-affordability/raw/main/data/pa_systems.geojson")

# create dir to store file and download
dir_create(path(data_path, "boundary/pa"))
download.file(pa_url, path(data_path, "boundary/pa/pa.geojson"))
cat("Downloaded PA polygon boundary data.\n")
