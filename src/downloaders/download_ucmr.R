# download UCMR occurrence data -----------------------------------------------

library(tidyverse)
library(glue)
library(fs)

# Allow for longer timeout for download file
options(timeout = 10000)

# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# Data Source: UCMR Program, which records zip codes served 
ucmr3_url <- paste0("https://www.epa.gov/sites/default/files/2017-02/",
                    "ucmr-3-occurrence-data.zip")

ucmr4_url <- paste0("https://www.epa.gov/sites/default/files/2020-04/",
                    "ucmr_4_occurrence_data.zip?VersionId=",
                    "m3C_dKBtBPyz35yDVL_1uZLjGjHiZtwf")

# create dir to store downloaded files
dir_create(path(data_path, "ucmr"))

# local paths to download files
file_ucmr3 <- path(data_path, "ucmr/ucmr3.zip")
file_ucmr4 <- path(data_path, "ucmr/ucmr4.zip")

# download and unzip
download.file(ucmr3_url, file_ucmr3)
download.file(ucmr4_url, file_ucmr4)

unzip(file_ucmr3, exdir = path(data_path, "ucmr"))
unzip(file_ucmr4, exdir = path(data_path, "ucmr"))

cat("Downloaded and unzipped UCMR3 and UCMR4 data.\n")
