# Discord Variant Scraper
Simple Discord bot that scrapes GISAID SARS-CoV-2 variant frequencies (https://www.gisaid.org/hcov19-variants/) from the past 4 weeks and parses them on a per-country basis. The variants are the Variants of Interest (VoI) and Variants of Concern (VoC) as listed by the WHO on https://www.who.int/en/activities/tracking-SARS-CoV-2-variants/. 

It is still in very early development. 
- ~~First thing on the list is adding saving to file by serialization, so the scrape() and parse() functions can properly operate independent from one another, saving website requests.~~ Done.
- Currently thinking of a method to ask variant-specific data, e.g. '!delta' could show some aggregate info from public health services, mutation profile, maybe some recent article urls/abstracts
- Also contemplating embedded images of graphs as an option instead of rows of percentages.

If a country does not appear in the output, it is because the bot was not able to find variant contribution for the specific GISAID variant (e.g. 'all null'-countries are ignored when parsing).

Percentages are shown in **bold** when exceeding 50% submission contribution to a country.

From GISAID: *"Observed frequencies are subject to sampling and reporting biases and do not represent exact prevalence."*

![Alt text](images/Github_Example2.png?raw=true "Variants percentages from GISAID")

![Alt text](images/Github_Example3.png?raw=true "WHO variant tables")
