# DiscordVariantScraper
Simple Discord bot that scrapes GISAID SARS-CoV-2 variant frequencies from the past 4 weeks and parses them on a per-country basis.

It is still in very early development. First thing on the list is adding saving to file by serialization, so the scrape() and parse() functions can properly operate independent from one another, saving website requests.

If a country dos not appear in the output, it is because the bot was not able to find variant contribution for the specific GISAID variant (e.g. 'all null'-countries are ignored when parsing).

Percentages are shown in **bold** when exceeding 50% submission contribution to a country.

From GISAID: *"Observed frequencies are subject to sampling and reporting biases and do not represent exact prevalence."*

![Alt text](images/Github_Example.png?raw=true "Title")
