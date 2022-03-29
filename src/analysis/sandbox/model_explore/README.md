# "model_explore" Little Saandbox

This little sandbox houses model exploration scripts used to prototype the final code in `src/model` and the March 2022 report summarizing construction of the TEMM data layer. 

## Table of contents

* `model_march.Rmd` summarizes construction of the TEMM data layer and uses flat files in `/etc` to render.  
* `02_random_forest.R` fits the random forest model.  
* `03_xgboost.R` fits the xgboost model.  

* `/archive` has two scripts:  
    - `01_preprocess.R` -> migrated to and superseded by `src/model/01_preprocess.R`  
    - `04_linear.R` -> migrated to and superseded by `src/model/02_linear.R`  
