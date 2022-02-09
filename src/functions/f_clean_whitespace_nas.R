# trim whitespace and replace common NA values with actual NAs
f_clean_whitespace_nas <- function(df){
  
  # if df is spatial, detach geometry before cleaning cols
  if(sum(class(mhp_sp) == "sf") == 1) {
    geom <- df$geometry
    df <- st_drop_geometry(df)
  }
    
  # apply whitespace and NA cleaning
  df <- dplyr::mutate_all(df, stringr::str_trim, "both") |>
    # all whitespace becomes "", so the next pattern handles all cases
    dplyr::mutate_all(dplyr::na_if, "") |>
    dplyr::mutate_all(dplyr::na_if, "NULL") |>
    dplyr::mutate_all(dplyr::na_if, "NA") |>
    dplyr::mutate_all(dplyr::na_if, "N/A")
  
  # reattach geometry if the object is spatial
  if(exists("geom")) {
    df <- st_as_sf(bind_cols(df, geometry = geom))
  }
  
  return(df)
}
