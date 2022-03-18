# Define UI for application that draws a histogram
shinyUI(fluidPage(

    # Application title
    titlePanel("Match Report Review"),

        mainPanel(
          fluidRow(
            # user input for pwsid
            selectizeInput(
              "input_pwsid",
              "Select a PWSID:",
              multiple = FALSE,
              choices  = pwsids
            ),
            # output leaflet for selected pwsid
            leafletOutput("output_leaflet"),
            HTML("<br><br>"),
            # datatable output for selected pwsid
            dataTableOutput("output_dt")
          )
        )
    )
)
