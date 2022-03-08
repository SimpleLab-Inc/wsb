# Download CT water system data -------------------------------------------

library(fs)

# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# Allow for longer timeout to map download file
options(timeout = 10000)

# Data Source: Connecticut ArcGIS shapefile water system boundary
ct_url <- paste0("https://portal.ct.gov/-/media/Departments-and-Agencies/",
                 "DPH/dph/drinking_water/GIS/",
                 "Buffered_Community_PWS_Service_Areas.zip")

# create dir to store folder and download
dir_path <- path(data_path, "boundary/ct")
file_path <- path(dir_path, "ct.zip")
dir_create(dir_path)
download.file(ct_url, file_path)
cat("Downloaded CT polygon boundary data.\n")

# unzip folder
unzip(zipfile=file_path, exdir=dir_path)
