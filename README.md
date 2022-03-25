# USA Water Service Boundary Proxy 

_Last updated 2022-03-25_  

## Project Background  

Water service boundaries (spatial polygons) delineate areas over which water is delivered from water systems to customers. Across the USA, some states (e.g., CA, TX, PA) maintain centralized water system boundary (henceforth, **wsb**) databases and make these accessible to the public. Publicly-accessible wsb data is not easily discoverable or cataloged for all states. 

In this work, we build a reproducible pipeline to assimilate existing wsb data in the USA (labeled data). We then match water system names, cities served, and facility centroids with spatial boundaries for Census places. We also engineer features that predict the approximate spatial extent of these boundaries and train statistical and machine learning models on these features to produce proxy water system boundaries for states without centralized wsb data. The result is a dataset of all potential geographic boundaries or features associated with each water system. We then apply a hierarchical selection, assigning the highest integrity spatial boundary (labeled water service area shapefile being the highest integrity; modeled boundary being the lowest integrity) to each water system. The result is a provisional water system boundary layer for active, community water systems across the US.    

## Project Organization

The main function of the project is an ETM (extract-transform-model) **pipeline** that chains a set of modular programs which can be flexibly modified over time to accommodate changes in input data and required output results. The main output in `/proxywsb` is a filesystem of various spatial formats (e.g., shp, geojson, csv, rds) that makes results of the proxy wsb model and labeled wsb data available for download and use. 

Download and transform data processing steps are modularized into separate processes in the `/src/downloaders` and `src/transformers` directories that can be modified and run in parallel, with no dependencies on one another. Downloaders pull raw data from the web to a local filesystem. See  [downloaders](https://github.com/SimpleLab-Inc/wsb/tree/develop/src/downloaders) directory. Transformers clean, standardize and join that data, and then write it to `data/staging`. See  [transformers](https://github.com/SimpleLab-Inc/wsb/tree/develop/src/transformers) directory.

The staged and standardized data is pulled into a matching model that joins all data sources together and assigns TIGER/Line places to water systems. See [matching](https://github.com/SimpleLab-Inc/wsb/tree/develop/src/analysis/sandbox/matching) directory. 

Finally, a model reads the output of the matched data and outputs a wsb proxy layer to `/proxywsb`. All data in this project is quite small and should easily fit into memory and on a PC. See [models](https://github.com/SimpleLab-Inc/wsb/tree/develop/src/analysis/sandbox/model_explore) directory.

Exploratory data analysis (EDA), sanity checks, and feature engineering experimentation occur in the **sandbox** (`src/analysis`) and are modularized into iterative notebooks and scripts that can serve multiple objectives without interfering with the functionality of the main ETM pipeline (i.e., `src/run.py`). This makes it easy to create and archive new analyses that serve a purpose, but that may never become productionized.  

The data science **contributor guide** in the [sandbox](https://github.com/SimpleLab-Inc/wsb/tree/develop/src/analysis) directory is a set of organizing guidelines for how EDA, analyses, and modeled output occur should be conducted in the **sandbox**.  

The overall **pipeline** is shown below:  

![](etc/diagram.png) 


## Getting started

Clone this repo.  

Install `R version 4.1.0`. Download packages as necessary. We rely only on version-stable CRAN packages. 

Set environmental variables in two files: `.env` (python) and `.Renviron` (R):

From command line in your repositories folder you can:

```
cd wsb
touch .Renviron

cd src
touch .env
```

Note: 
`.Renviron` needs to be set up in the root directory, `wsb/` to work with projects.
`.env` needs to be set up in `wsb/src`.

To add variables, open both environment files, copy and paste into each:


```
WSB_DATA_PATH = "path to save raw data from downloaders"
WSB_STAGING_PATH = "path to stage post-transformer data for EDA and modeling"
WSB_EPSG = "4326"
WSB_EPSG_AW = "ESRI:102003"
```
Don't forget to leave a blank line at the end of `.Renviron` before saving.

To associate `.Renviron` with the `R` project, open `R`, run `usethis::edit_r_environ(scope = "project")`. 
  
`WSB_DATA_PATH` is where we save raw data from the downloaders, which may grow sizable and be better placed off disk.  

`WSB_STAGING_PATH` is where we stage post-transformed for EDA and modeling.  

Use `WSB_EPSG` when writing to geojson, and `WSB_EPSG_AW` when calculating areas on labeled geometries
`WSB_EPSG_AW` is the coordinate reference system (CRS) used by transformers when we make calculations. We currently use [Albers Equal Area Conic projected CRS](https://epsg.io/102003) for equal area calculations. For AK and HI, we need to shift geometry into this CRS so area calculations are minimally distorted, see `tigris::shift_geometry(d, preserve_area = TRUE)` at [this webpage](https://walker-data.com/census-r/census-geographic-data-and-applications-in-r.html#shifting-and-rescaling-geometry-for-national-us-mapping). `WSB_EPSG` is a World Geodetic System 1984 (see [here](https://epsg.io/4326)) which is the CRS that geojson stores.


## Python venv and requirements

Create a virtual environment, activate it, and install package dependencies:  

On Windows:  

```
python -m venv .venv
.venv/scripts/activate.bat
pip install -r requirements.txt
```

Install `aria` for downloading large files. Preferred method is to use the [chocolatey package manager](https://chocolatey.org/):  

```
choco install aria2
```

On OSX/Linux:  

With conda:
```
conda install -n sl
conda activate sl
```

with venv
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Install `aria` for downloading files:  

```
brew install aria2
```

Self-solve system-specific issues.  


## R requirements

We use a ["snapshot and restore"](https://environments.rstudio.com/snapshot.html) approach to dependency management for Python and R environments. This may be superceeded by Docker at a later time.  

Download RStudio, then open `wsb.RProject` in RStudio. This will bootstrap `renv`. Next, in the R console, run `renv::restore()` to install R package dependencies and self-solve system-specific issues.  

When a developer updates or installs new packages to the R project, the lockfile must be updated. Steps include:

1. A user installs, or updates, one or more packages in their local project library;  
2. That user calls `renv::snapshot()` to update the `renv.lock` lockfile;  
3. That user then shares the updated version of `renv.lock` with their collaborators by pushing to Github;  
4. Other collaborators then call `renv::restore()` to install the packages specified in the newly-updated lockfile.  


## Contributing 

To contribute to the project, please branch from `develop` or a subbranch of `develop` and submit a pull request. To be considered as a maintainer, please contact Jess Goddard <jess at gosimplelab dot com>. 
