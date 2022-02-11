# download ECHO admin data -----------------------------------------------

library(tidyverse)
library(glue)
library(fs)

# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# Allow for longer timeout for download file
options(timeout = 10000)

# Data Source: EPA's ECHO Exporter ZIP and SDWA zip (in case it is useful)
echo_url <- paste0("https://echo.epa.gov/files/echodownloads/",
                  "echo_exporter.zip")

sdwa_url <- paste0("https://echo.epa.gov/files/echodownloads/",
                   "SDWA_latest_downloads.zip")

# create dir to store file, download, and un-zip
dir_create(path(data_path, "echo"))

download.file(echo_url, path(data_path, "echo/echo_exporter.zip"))
download.file(sdwa_url, path(data_path, "echo/sdwa.zip"))

unzip(path(data_path, "echo/echo_exporter.zip"), exdir = path(data_path, "echo"))
unzip(path(data_path, "echo/sdwa.zip"), exdir = path(data_path, "echo"))

cat("Downloaded and unzipped ECHO (and SDWA) data.\n")