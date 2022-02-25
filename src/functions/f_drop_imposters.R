# drops imposters, which are geometries that report being in one state
# but that actually are located in another. This function filters to 
# valid rows where input geom falls within state geoms (non-imposters),
# and sinks a log file of invalid geoms (imposters) to review. 
# See GH Issue #45:  https://github.com/SimpleLab-Inc/wsb/issues/45

f_drop_imposters <- function(d, path_log){
  
  # error if the supplied input is not sf
  if(!"sf" %in% class(d)){
    stop("Input object is not of type `sf`.", call. = FALSE)
  }
  
  # error if the supplied object does not have a PWSID field name
  if(!"state" %in% colnames(d)){
    stop("Column `state` missing from input object.", call. = FALSE)
  }
  
  # if the log path doesn't exist, create it
  if(!dir_exists(here::here("log"))) dir_create(here::here("log"))
  
  # reported state name 
  d = rename(d, state_reported = state)
  
  # create state name to abbreviation key with built-in R objects
  key = tibble(name = state.name, state_intersection = state.abb)
  
  # pull usa state geometries, project to input data CRS
  usa = USAboundaries::us_states(resolution = "high") %>% 
    st_transform(st_crs(d)$epsg) %>% 
    select(state_intersection = state_abbr, geometry) %>% 
    suppressMessages()
  
  # spatial join input data to usa state polygons.
  # filter to valid and invalid geometries for returned objects
  cat("Joining input object geometries to USA state polygons...")
  d_joined = st_join(d, usa) 
  cat("done.\n\n")
  
  # valid geometries: reported state == intersected state
  d_valid = d_joined %>% 
    filter(
      state_reported == state_intersection |
      # also return when an input geometry doesn't intersect the USA geom
      is.na(state_intersection)
    ) %>% 
    select(-state_reported, -state_intersection)
  
  # imposters: reported state != intersected state
  d_imposter = d_joined %>% 
    filter(
      state_reported != state_intersection | 
      # also return when a state isn't reported
      is.na(state_reported)
    ) %>% 
    select(state_reported, state_intersection, everything()) %>% 
    st_drop_geometry()
  
  # print stats on valid/invalid geometries
  nrow_d   = nrow(d_joined)   %>% formatC(big.mark = ",")
  nrow_dv  = nrow(d_valid)    %>% formatC(big.mark = ",")
  nrow_imp = nrow(d_imposter) %>% formatC(big.mark = ",")
  p_valid  = round(((nrow(d_valid)/nrow(d_joined))*100), 2)

  cat(nrow_dv, "/", nrow_d, "rows are valid", "(", 
      p_valid, "% of input data).\n\n")
  
  # sink invalid pwsids (even with dupes, e.g. FRS) to a log file
  write_csv(d_imposter, path_log)
  cat("Wrote", nrow_imp, "imposters for review to", path_log, "\n")
  
  # return valid geometries as an object
  return(d_valid)
  cat("Returned valid goemetries in return object.\n\n")
}
