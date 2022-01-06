# Discord Variant Scraper
Discord bot that scrapes GISAID SARS-CoV-2 variant frequencies (https://www.gisaid.org/hcov19-variants/) from the past 4 weeks and parses them on a per-country basis. Countries with 0 sequences in the past 4 weeks are skipped. Countries sorted by sequence contribution. The variants are the Variants of Interest (VoI) and Variants of Concern (VoC) as listed by the WHO on https://www.who.int/en/activities/tracking-SARS-CoV-2-variants/. 

TO-DO:
- Currently thinking of a method to ask variant-specific data, e.g. '!delta' could show some aggregate info from public health services, mutation profile, maybe some recent article urls/abstracts

From GISAID: *"Observed frequencies are subject to sampling and reporting biases and do not represent exact prevalence."*

![Alt text](images/Github_Example2.png?raw=true "Variants percentages from GISAID")

![Alt text](images/ecdc1.png?raw=true "Variant tables")

![Alt text](images/ecdc2.png?raw=true "Variant tables")
