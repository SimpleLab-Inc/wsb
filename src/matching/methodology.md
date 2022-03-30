# Methodology

We have several data sources that contain opinions about PWS's, such as their name, addresses, lat/long, and boundaries. These different data sources vary in quality and comprehensiveness.

For example, SDWIS is the "system of record" for identifying which PWS's exist and what their PWS ID's are; but it does not contain lat/long, and the addresses stored in SDWIS are often low-quality PO Boxes or administrative addresses, rather than the address of the water system itself.

ECHO contains lat/long, but it is also frequently low-quality. In many cases, it simply provides the centroid for the zip code, county, or state in which the facility is located.

Since each of these data sources have some information to contribute, they will be known as **contributors**. Ultimately, we hope to create a CSV where each row represents a single, unique public water system, and the best attributes have been selected from each of the contributors to create a **master record**. These master records are uniquely identified by their PWS ID's.

In order to create the most complete master records, we need to link as many contributors as possible to their corresponding master records. Some of our data sources (SDWIS, ECHO, FRS, and UCMR) are labeled with PWS ID's, which make them easy to match together. Other data sources (MHP, TIGER) do not have PWS ID's, so we have to rely on other attributes, fuzzier match logic, and various manual and automatic reviews to try to match these to their relevant PWS ID's.

The process for matching these together is described below.

## Mapping
Map all the data sources into a standard model, unioned on top of one another. That is, instead of one system having a column "pws_name" and another system having a column "FacName", we simply standardize them all to "name". This allows us to compare differences across the systems easily. Stacking them in a single table allows us to apply various sorts and joins that identify potential matches.

Since all the records are being stacked, we populate a few additional fields to help track their lineage:
- `source_system` - The name of the data source that contributed the row
- `source_system_id` - The ID which uniquely identifies the row within the source system
- `contributor_id` - An ID which uniquely identifies the record across _all_ systems. It is created by concatenating the `source_system` with the `source_system_id`,
- `master_key` - When we know the PWS ID for a particular row, that is the "master key" for the row. When we don't know the PWS ID, we store an arbitrary unique ID.

## Cleansing
Apply various "cleansing" steps to improve data quality and improve the matching. For example, all text fields are upper-cased. PO Boxes are removed from the address field, because we only care about actual facility addresses. Nonexistent zip codes (99999) are removed. These rules can be expanded in many ways to improve the quality of the data.

## Tokenizing
Create "tokens" to prepare for matching. If we're trying to match facility names together, the names "LAKE WALES, CITY OF" and "LAKE WALES" would not match by default. But we can apply a series of string modifications to reduce these variations and increase the likelihood of matching.

Our tokenization function:
1. Removes common terms like "CITY OF", "COMMUNITY WATER SYSTEM", "WSD", etc.
2. Removes punctuation.
3. Replaces multiple-whitespace characters with a single cahracter.
4. Trims off whitespace from beginning / end of the string.

After these steps, "LAKE WALES, CITY OF" and "LAKE WALES" will both become "LAKE WALES" and matching will be more effective.

## Matching
Run a series of match rules. Each rule is implemented as a simple join between tables. On the left side, we usually have one or more of our "anchor" systems (SDWIS, ECHO, FRS) in which we already know the PWS ID. On the right side, we have the "candidate" systems (TIGER, MHP) in which we don't know the PWS ID. Then we set a variety of criteria constraining how the join works.

For example, on the state+name match, we constrain the left side to only SDWIS, ECHO, and FRS rows in which the "state" and the "name_tkn" (containing the results of the name tokenization function) fields are populated. We constrain the right side to only TIGER and MHP rows in which "state" and "name_tkn" are populated. We then join the left to the right side where both sides match on "state" and "name_tkn". This gives us a series of "match pairs" between contributors.

Since there are often multiple contributors on the left side for the same PWS ID, we end up with some duplication. So we simplify these match pairs by converting the left contributor ID to its master key, then group them up. We end up with a table containing: master key (the unique PWS identifier), candidate_contributor_id (the contributor that *might* be linked to the master), and match_rule (the reasons these two records matched). We save this resulting table to the database.

## Reporting
To determine whether our match rules are generating accurate matches, we generate a few reports for manual review.

The **stacked match report** displays groupings of contributors so that you can easily compare their attributes and determine if they belong together.

The **unmatched report** displays a long list of the records that did not successfully match to anything. You can manually sort and comb through this data to see if you can identify the correct matches, and develop intuitions as to why they did not match.


## Superjoin
The matches can be problematic, because we don't know for sure that they are correct matches; they are only "candidates." It's also possible for a record to match to more than one candidate of the same type, which is likely inaccurate. For example, a PWS should really only match to one "best" TIGER record, but the matches frequently generate 2 or 3 TIGER matches.

We need to make decisions about which "candidate matches" are correct. The superjoin attempts to apply some logic to do this. This logic can be refined over time.