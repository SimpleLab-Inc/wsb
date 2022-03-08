# Download OR water system data -------------------------------------------

library(fs)

# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# Allow for longer timeout to map download file
options(timeout = 10000)

# Data Source: Oregon ArcGIS geojson water system boundary
or_url <- paste0("https://github.com/NIEPS-Water-Program/",
                 "water-affordability/raw/main/data/or_systems.geojson")

# create dir to store file and download
dir_create(path(data_path, "boundary/or"))
download.file(or_url, path(data_path, "boundary/or/or.geojson"))
cat("Downloaded OR polygon boundary data.\n")
