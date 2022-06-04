# download ECHO admin data -----------------------------------------------

library(glue)
library(fs)

# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# Allow for longer timeout for download file
options(timeout = 10000)

# Data Source: EPA's ECHO Exporter ZIP and SDWA zip (in case it is useful)
echo_url <- paste0("https://echo.epa.gov/files/echodownloads/",
                   "echo_exporter.zip")
# create dir to store file, download, and un-zip
dir_create(path(data_path, "echo"))

# local path to download files
file_echo <- path(data_path, "echo/echo_exporter.zip")

download.file(echo_url, file_echo)

unzip(file_echo, exdir = path(data_path, "echo"))

cat("Downloaded and unzipped ECHO data.\n")
