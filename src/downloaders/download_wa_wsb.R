# Download WA water system data -------------------------------------------

library(fs)

# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# Allow for longer timeout to map download file
options(timeout = 10000)

# Data Source: Washington ArcGIS Geodatabase water system boundary
url <- paste0("https://opendata.arcgis.com/datasets/",
              "b09475f47a5a46ca90fe6a168fb22e6d_0.geojson")

# create dir to store folder and download
dir_path <- path(data_path, "boundary/wa")
file_path <- path(dir_path, "wa.zip")
dir_create(dir_path)
download.file(url, file_path)
cat("Downloaded WA polygon boundary data.\n")

# unzip folder
unzip(zipfile=file_path, exdir=dir_path)
