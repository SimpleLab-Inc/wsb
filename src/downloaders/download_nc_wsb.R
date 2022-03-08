# Download NC water service boundaries ------------------------------------

library(fs)

# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# Allow for longer timeout to map download file
options(timeout = 10000)

# Data Source: North Carolina ArcGIS geojson water system boundary
# https://hub.arcgis.com/datasets/nconemap::type-a-current-public-water-systems-2004/
nc_url <- paste0("https://opendata.arcgis.com/datasets/",
                 "30cf567422ec4930ae0b0c8544f8263f_1.geojson")

# create dir to store file and download
dir_create(path(data_path, "boundary/nc"))
download.file(nc_url, path(data_path, "boundary/nc/nc.geojson"))
cat("Downloaded NC polygon boundary data.\n")
