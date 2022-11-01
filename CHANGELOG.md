# Water Service Boundaries - Change Log

# 3.0.0 (2022-10-31)
* Adding manually-contributed systems from the Internet of Water's [Github](https://github.com/cgs-earth/ref_pws/raw/main/02_output/contributed_pws.gpkg)
* Refactored to use geopackage through most of pipeline instead of geojson
* Added `geometry_source_detail` column, to document where the data provider got the geometries from

# 2.4.0 (2022-09-27)
* Added Arkansas labeled boundaries. The original data source did not have water system ids, but a match on names was pretty comprehensive. We supplemented with ~40 manually looked-up water system ids based on the remaining non-matches. There are still 12 systems with shapefiles from the underlying data that did not actually have any water system id that I could match.

# 2.3.0 (2022-09-02)
* Added Rhode Island labeled boundaries. The original data source did not include PWS ID's, so these were supplemented by manual effort from the EPIC team.

# 2.2.0 (2022-08-23)
* With version 2.0, we changed logic to eliminate Tier 2b, meaning only one PWS could "own" any particular tiger place. This caused many PWS's that were formerly Tier 2b to fall back to Tier 3. In some cases, these relied on low-quality county or state centroids from Echo, resulting in a less accurate map. In this release, we addressed this problem. For PWS's that (1) have a low-quality centroid and (2) have a matched tiger boundary, but (3) were not selected as the "best" match for that boundary, we overwrite the centroid with a calculated centroid from the top-ranked matched boundary.
* Refactor to preserve all "ranked" boundary matches, not just the "best" match.
* Saving the final "master" records back to the database
* Added "tier" column to the database


# 2.1.0 (2022-08-09)
* Improved logic for how "impostors" are calculated. Here is a summary of impacts:

| Category | Echo | FRS | Reason |
|----------|-------|-----|-----------|
| Rejected only before | 114 | 336 | 20 echo and 1 FRS are now allowed because they're within 50 km of the primacy agency's border. 326 FRS are no longer in the system at all, now that the ECHO's are coming through (the FRS mapping is unusual in that it doesn't load records if they're already coming through via ECHO, since FRS is largely duplicates of ECHO). 9 FRS were rejected for being tribal regions and not recognizing the primacy_agency_code as a state. 91 ECHO's had NULL state. |
| Rejected both times | 6 | 26 | Legit impostors, identified both times. |
| Rejected only after | 292 | 0 | These were previously allowed because the lat/long was consistent with the _address's state_, but not of the _primacy agency_. In the new logic, I do allow it to be outside of the primacy_agency state, but not further than 50 km away. |


# 2.0.0 (2022-07-01)
* No longer dropping any PWS's (but some results have tier "none", indicating no geometry)
* Added Utah and Illinois labeled boundaries
* Eliminated Tier 2b by implement ranking and selection of best PWS per Tiger. Roughly 3000 became Tier 2a, remaining 7000 became Tier 3
* Renamed some columns:
  * geometry_lat -> centroid_lat
  * geometry_lon -> centroid_lon
  * geometry_quality -> centroid_quality
  * tiger_geoid -> matched_bound_geoid
  * tiger_name -> matched_bound_name
* Cleaned up column names in the shapefile
* Improved matching to MHPs, and prevented MHP's from matching to Tiger places
* Pulled in population data for Tiger places, to help deduplicate matches
* Misc bugfixes and performance improvements

| Tier 1  | Tier 2a | Tier 2b  | Tier 3  | None   | Total  |
|---------|---------|----------|---------|--------|--------|
| 16,896  | 11,526  | 0        | 17,526  | 3,476  | 49,424 |


# 1.0.0 (2022-05-02)
Initial release

| Tier 1  | Tier 2a | Tier 2b  | Tier 3  | None  | Total   |
|---------|---------|----------|---------|-------|---------|
| 14,607  | 9,488   | 10,104   | 10,720  | 0     | 44,919* |

*Note: 4505 systems were dropped due to missing geometry or not falling within 50 US states.
