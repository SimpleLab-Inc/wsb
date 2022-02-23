# download UCMR occurrence data -----------------------------------------------

library(tidyverse)
library(glue)
library(fs)

# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# Allow for longer timeout for download file
options(timeout = 10000)

# Data Source: UCMR Program, which records zip codes served 
ucmr3_url <- paste0("https://www.epa.gov/sites/default/files/2017-02/",
                    "ucmr-3-occurrence-data.zip")

ucmr4_url <- paste0("https://www.epa.gov/sites/default/files/2020-04/",
                      "ucmr_4_occurrence_data.zip?VersionId=m3C_dKBtBPyz35yDVL_1uZLjGjHiZtwf")

# create dir to store file, download, and un-zip
dir_create(path(data_path, "ucmr"))

# local path to download files
file_ucmr3 <- path(data_path, "ucmr/ucmr3.zip")
file_ucmr4 <- path(data_path, "ucmr/ucmr4.zip")

download.file(ucmr3_url, file_ucmr3)
download.file(ucmr4_url, file_ucmr4)

unzip(file_ucmr3, exdir = path(data_path, "ucmr"))
unzip(file_ucmr4, exdir = path(data_path, "ucmr"))

cat("Downloaded and unzipped UCMR3 and UCMR4 data.\n")
