#!/usr/bin/env python3

# Author:       tch
# Date:         05-08-2021 (dd/mm/yyyy)
# Description:  First attempt at a Discord bot to scrape and parse 
#               relative variant frequencies that are submitted to GISAID.
#               All data belongs to their respective GISAID uploaders.
# To-do:
# - command for variant-specific info
# - wrapper for scrape/parse?
# - make up my mind about output formatting...

from os import EX_CANTCREAT
from discord.ext import commands
import requests, re, json
import country_converter as coco
import pickle
from lxml import etree

# verification token for bot
with open('variant_token.txt','r') as tokenfile:
    TOKEN = tokenfile.read()
assert TOKEN != ""

# define command prefix and global vars
bot = commands.Bot(command_prefix='!')
variants = None
countries = None
var_perc = None

# scrape GISAID data
@bot.command()
async def scrape(ctx):
    print("Scraping...")
    global variants, countries, var_perc
    # get config with actual variants displayed
    pageconfig = requests.get('https://mendel3.bii.a-star.edu.sg/METHODS/corona/gamma/MUTATIONS/data/config.json')
    pageconfig = pageconfig.text
    if not pageconfig:
        return
    variants = []
    # find tooltip variant abbrevations
    tooltip_reg = re.search('(?s)"tooltipName":\s\{(.+?)\}', pageconfig)
    if tooltip_reg:
        tooltip = tooltip_reg.group(1)
        # find individual variants
        var_reg = re.findall('"([a-z0-9]+)":\s+"(.+?)"', tooltip)
    if not var_reg:
        return
    for var in var_reg:
        variants.append(var)

    # from here all data from the past 4 weeks will be scraped, on a per variant basis
    pre_url = "https://mendel3.bii.a-star.edu.sg/METHODS/corona/gamma/MUTATIONS/data/countryCount_{}.json"
    var_perc = {}
    countries = []
    for variant in variants:
        var, descrip = variant
        var_url = pre_url.format(var)
        var_text = requests.get(var_url).text
        if not var_text:
            return
        var_json = json.loads(var_text)
        for i in range(0,len(var_json)):
            country = var_json[i]['country']
            if country not in countries:
                countries.append(country)
            if var not in var_perc.keys():
                var_perc[var] = {var_json[i]['country']:var_json[i]['percvui_last4wks']}
            else:
                var_perc[var].update({var_json[i]['country']:var_json[i]['percvui_last4wks']})
        print(str(variant)+" done")
    # save scraped data to file
    print("Saving to file...")
    with open("data.pickle","wb") as f:
        pickle.dump([variants,countries,var_perc], f)
    await ctx.send("> GISAID has been scraped. :white_check_mark:")

# parse scraped data to Discord
@bot.command()   
async def parse(ctx):
    global variants, countries, var_perc
    # check if empty vars, if so -> try loading from file
    if any([var == None for var in [variants, countries, var_perc]]):
        try:
            print("Reading data from file")
            with open("data.pickle","rb") as f:
                variants, countries, var_perc = pickle.load(f)
            if any([var == None for var in [variants, countries, var_perc]]):
                print("One or more files were empty, rerun !scrape")
        except IOError as io:
            print("Can't read the save file! Fix permission issues or rerun !scrape")
            print(io)
        except Exception as e:
            print("Non-IOError, try rerunning !scrape")
            print(e)
    discl1 = "**> DISCLAIMER**"
    discl2 = "> This bot scrapes the relative percentages of genome **submissions of the past 4 weeks** from the tracked variants to GISAID. The variants are limited to the Variants of Concern and Variants of Interest as listed by the WHO (https://www.who.int/en/activities/tracking-SARS-CoV-2-variants/)."
    discl3 = "> Observed frequencies are subject to sampling and reporting biases and **do not** represent exact prevalence."
    discl4 = "> See https://www.gisaid.org/hcov19-variants/ for more info."
    disclaimers = [discl1,discl2,discl3,discl4]
    await ctx.send("\n".join(disclaimers))

    # parse percentages per country, per variant
    for country in countries:
        percs = []
        for var,descrip in variants:
            try:
                percs.append("{:2.1f}".format(var_perc[var][country]))
            # no data for this country in the json
            except KeyError:
                percs.append("0.0")
            # other errors
            except Exception as e:
                print(e)
        # check if country only contains "0.0"
        if any([perc!="0.0" for perc in percs]):
            # change country name to iso-code and flag
            iso = coco.convert(country, to="ISO2")
            flag_iso = ' :flag_'+iso.lower()[:2]+':'
            sent1 = "**> "+flag_iso+" "+country+"**"
            # zip variants with percentages
            results = list(zip([var[1].split()[0] for var in variants], percs))
            sent2 = "> \t\t\t\t"+"\t".join(["{}: {}".format(
                res[0],res[1]) if float(res[1])<50 
                else "{}: **{}**".format(res[0],res[1]) 
                for res in results])
            await ctx.send(sent1)
            await ctx.send(sent2)
        else:
            print(country, percs)
    await ctx.send("> All countries parsed. :white_check_mark:")

def text(elt):
    return elt.text_content().replace(u'\xa0', u' ')

# Retrieve variant-specific aggregate info
@bot.command()   
async def vars(ctx):
    global variants
    print("\n\n\n\n\n\n")
    # retrieve WHO variants text
    who_page = requests.get("https://www.who.int/en/activities/tracking-SARS-CoV-2-variants/")
    if who_page:
        tree = etree.HTML(who_page.content)
    # parse variant meta info from xpath

    # VOC
    voc_table = []
    columns = [1,2,5,6]
    rows = len(variants) if variants != None else 10
    for i in range(1,rows):
        for j in columns:
            try: # to catch empty rows
                print(i,j)
                td = None
                td = tree.xpath('//*[contains(@id,"PageContent_C238")]/div/div/table/tbody/tr[{}]/td[{}]/p'.format(i,j))
                #print(td)
                if not td == []:
                    for k in td:
                        content = etree.tostring(k)
                        print(content)
                        voc_table.append(content)
                else:
                    td = None
                    td = tree.xpath('//*[contains(@id,"PageContent_C238")]/div/div/table/tbody/tr[{}]/td[{}]'.format(i,j))
                    for k in td:
                        print(k.text)
                        content = etree.tostring(k)
                        print(content)
                        voc_table.append(content)
            except:
                continue
    print(voc_table)

    general_info = """The WHO currently categorizes two groups of variants:

**Variants of Concern (VOC):**
A SARS-CoV-2 variant that meets the definition of a VOI (see below) and, through a comparative assessment, has been demonstrated to be associated with one or more of the following changes at a degree of global public health significance: 
    - Increase in transmissibility or detrimental change in COVID-19 epidemiology; OR
    - Increase in virulence or change in clinical disease presentation; OR
    - Decrease in effectiveness of public health and social measures or available diagnostics, vaccines, therapeutics.  
    
**Variants of Interest (VOI):**
A SARS-CoV-2 variant : 
    - with genetic changes that are predicted or known to affect virus characteristics such as transmissibility, disease severity, immune escape, diagnostic or therapeutic escape; AND 
    - Identified to cause significant community transmission or multiple COVID-19 clusters, in multiple countries with increasing relative prevalence alongside increasing number of cases over time, or other apparent epidemiological impacts to suggest an emerging risk to global public health."""
    #await ctx.send(general_info)
    pass

bot.run(TOKEN)
