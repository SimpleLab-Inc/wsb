# download SDWIS admin data -----------------------------------------------

library(tidyverse)
library(glue)
library(fs)

# path to save raw data
data_path <- Sys.getenv("WSB_DATA_PATH")

# Allow for longer timeout to map download file
options(timeout = 10000, readr.show_progress = FALSE)

# sdwis cateogories to download, these go into the URL
sdwis_categories <- c("SERVICE_AREA", "GEOGRAPHIC_AREA",
                      "WATER_SYSTEM", "WATER_SYSTEM_FACILITY")

# create dir to store file and download
dir_create(path(data_path, "sdwis/"))

# save downloaded files to these paths
paths_out <- glue("{data_path}/sdwis/{tolower(sdwis_categories)}.csv")

# setup row indices and chunk size for download URL
nrow_max   <- 200000000 # 200M
chunk_size <- 10000     # 10k = chunk size limit for SDWIS web service
row_start  <- c(0, seq(chunk_size, nrow_max, chunk_size))
row_end    <- c(row_start[-1] - 1, nrow_max - 1)

for(i in seq_along(paths_out)){
  
  cat("Downloading SDWIS:", sdwis_categories[i], "\n")
  
  # empty vector to store results
  d <- vector("list", length = length(row_start))
  
  # download files until the download returns an empty set
  for(j in seq_along(row_start)){

    cat("    Downloading chunk [", j, "/", length(row_start), 
        "], rows:", row_start[j], ":", row_end[j], "...")
    
    # url to download for the jth chunk
    url <- paste0("https://data.epa.gov/efservice/", sdwis_categories[i],
                  "/ROWS/", row_start[j], ":", row_end[j], "/csv")
    
    # read url and suppress benign messages and warnings.
    # store all cols as character to ensure they all bind later on!
    d[[j]] <- read_csv(url) %>% 
      mutate(across(everything(), ~as.character(.x))) %>% 
      suppressWarnings() %>% 
      suppressMessages()
    
    cat("done.\n")
    
    # if an empty set is returned, break the loop 
    if(nrow(d[[j]]) == 0){
      cat("    Last loop returned 0 rows. Terminating.\n")
      break
    }
    
  }
  
  # combine all downloaded chunks for the ith dataset and save 
  d <- bind_rows(d) 
  write_csv(d, paths_out[i])
  
  cat("Downloaded and saved", j, "chunks of", sdwis_categories[i], 
      "data totaling", nrow(d), "rows.\n\n")
  
}
