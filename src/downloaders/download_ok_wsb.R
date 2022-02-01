# Download OK water system data -------------------------------------------

library(fs)

# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# Allow for longer timeout to map download file
options(timeout = 10000)

# Data Source: Oklahoma ArcGIS geojson water system boundary
ok_url <- paste0("https://opendata.arcgis.com/datasets/",
                 "d015bc14d3b84b8985ff3a4fd55c0844_0.geojson")

# create dir to store file and download
dir_create(path(data_path, "boundary/ok"))
download.file(ok_url, path(data_path, "/boundary/ok/ok.geojson"))
cat("Downloaded OK data.\n")
