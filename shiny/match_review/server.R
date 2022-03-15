shinyServer(function(input, output) {

    # create the output leaflet object
    output$output_leaflet <- renderLeaflet({
      
        # filter matches to user-selected pwsid (d't' for 'table')
        dt = filter(dmatch, mk_match == input$input_pwsid) %>% 
          # flag empty geom and geom type
          mutate(
            is_empty = st_is_empty(geometry),
            st_type  = st_geometry_type(geometry)
          )
        
        # troubleshooting code to step inside the user selection
        # dt = slice(dmatch, 1:3) %>% 
        #   mutate(
        #     is_empty = st_is_empty(geometry),
        #     st_type  = st_geometry_type(geometry)
        #   )

        # filter out empty points for leaflet
        dl = dt %>% filter(is_empty == FALSE) %>% 
          mutate(popup = paste(
            source_system, name, pwsid, sep = "<br>")
          )
        
        # separate point and polygon geoms
        point = dl %>% filter(st_type == "POINT") 
        poly  = dl %>% filter(st_type %in% c("POLYGON", "MULTIPOLYGON")) 
        
        # render the leaflet
        leaflet() %>% 
          addTiles() %>% 
          addPolygons(
            data  = poly,
            popup = poly$popup
          ) %>%
          addCircleMarkers(
            data = point, 
            popup = point$popup,
            color = "red"
          )

    })
    
    # render the data table output
    output$output_dt <- renderDataTable({
      
      # filter matches to the user-selected pwsid (dt for table)
      filter(dmatch, mk_match == input$input_pwsid) %>% 
        datatable(rownames = FALSE)
      
    })

})
