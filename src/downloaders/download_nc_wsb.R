# Download NC water service boundaries ------------------------------------

library(fs)

# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# Allow for longer timeout to map download file
options(timeout = 10000)

# Data Source: North Carolina ArcGIS geojson water system boundary
# https://hub.arcgis.com/datasets/nconemap::type-a-current-public-water-systems-2004/
nc_url <- paste0("https://opendata.arcgis.com/datasets/",
                 "58548b90bdfd4148829103ac7f4db9ce_4.geojson")

# create dir to store file and download
dir_create(path(data_path, "boundary/nc"))
download.file(nc_url, path(data_path, "/boundary/nc/nc.geojson"))
cat("Downloaded NC polygon boundary data.\n")
