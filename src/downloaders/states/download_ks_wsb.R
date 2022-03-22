# Download KS water system data -------------------------------------------

library(fs)

# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# Allow for longer timeout to map download file
options(timeout = 10000)

# Data Source: Kansas ArcGIS shapefile water system boundary
url <- paste0("https://data.kansasgis.org/catalog/",
                 "administrative_boundaries/shp/pws/PWS_bnd_2021_0430.zip")

# directory and file path
dir_path <- path(data_path, "boundary/ks")
file_path <- path(dir_path, "ks.zip")

# create directory, download file and unzip
dir_create(dir_path)
download.file(url, file_path)
unzip(zipfile=file_path, exdir=dir_path)

cat("Downloaded KS polygon boundary data.\n")