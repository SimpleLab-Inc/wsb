# Download WA water system data -------------------------------------------

library(fs)

# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# Allow for longer timeout to map download file
options(timeout = 10000)

# Data Source: Washington ArcGIS Geodatabase water system boundary
url <- paste0("https://fortress.wa.gov/doh/base/gis/ServiceAreas.zip")

# directory and file path
dir_path <- path(data_path, "boundary/wa")
file_path <- path(dir_path, "wa.zip")

# create directory, download, and unzip file
dir_create(dir_path)
download.file(url, file_path)
unzip(zipfile=file_path, exdir=dir_path)

cat("Downloaded and unzipped WA polygon boundary data.\n")

