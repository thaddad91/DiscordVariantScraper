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

import discord
from os import EX_CANTCREAT
from discord.ext import commands
import requests, re, json
import country_converter as coco
import pickle
from lxml import etree
import imgkit
from requests.api import head
#from PIL import Image, ImageChops

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
                else "**{}:** **{}**".format(res[0],res[1]) 
                for res in results])
            await ctx.send(sent1)
            await ctx.send(sent2)
        else:
            print(country, percs)
    await ctx.send("> All countries parsed. :white_check_mark:")

def text(elt):
    return elt.text_content().replace(u'\xa0', u' ')

# Retrieve variant information from the ECDC
@bot.command()   
async def variants(ctx):
    global variants
    #who_page = requests.get("https://www.who.int/en/activities/tracking-SARS-CoV-2-variants/")
    #if who_page:
    #    tree = etree.HTML(who_page.content)

    ecdc_page = requests.get("https://www.ecdc.europa.eu/en/covid-19/variants-concern")
    if ecdc_page:
        tree = etree.HTML(ecdc_page.content)
    # VoC table
    #voc = tree.xpath('//*[@id="PageContent_C238_Col01"]/div/div/table') # WHO
    #for v in voc:
    #    v = str(etree.tostring(v)).rstrip("'").lstrip("b'")
    #    imgkit.from_string(v,'voc.png')
    # VoI table
    #voi = tree.xpath('//*[@id="PageContent_C237_Col01"]/div/div/table') # WHO
    #for v in voi:
    #    v = str(etree.tostring(v)).rstrip("'").lstrip("b'")
    #    imgkit.from_string(v,'voi.png')

    # Scrape all variant tables from ECDC
    tables = tree.xpath('//table[@class="GridTable4-Accent61 table table-bordered table-striped"]')
    files = []
    for i,t in enumerate(tables):
        v = str(etree.tostring(t)).rstrip("'").lstrip("b'").replace('\\n','').replace('\\t','')
        filename = 'voi_{}.png'.format(i)
        files.append(filename)
        imgkit.from_string(v,filename)

    # VoC / VoI description from WHO
    general_info = """>>> The WHO currently categorizes two groups of variants:

**Variants of Concern (VOC):**
A SARS-CoV-2 variant that meets the definition of a VOI (see below) and, through a comparative assessment, has been demonstrated to be associated with one or more of the following changes at a degree of global public health significance: 
    - Increase in transmissibility or detrimental change in COVID-19 epidemiology; OR
    - Increase in virulence or change in clinical disease presentation; OR
    - Decrease in effectiveness of public health and social measures or available diagnostics, vaccines, therapeutics.  
    
**Variants of Interest (VOI):**
A SARS-CoV-2 variant : 
    - with genetic changes that are predicted or known to affect virus characteristics such as transmissibility, disease severity, immune escape, diagnostic or therapeutic escape; AND 
    - Identified to cause significant community transmission or multiple COVID-19 clusters, in multiple countries with increasing relative prevalence alongside increasing number of cases over time, or other apparent epidemiological impacts to suggest an emerging risk to global public health. \n\n"""
    #await ctx.send(general_info)
    #for img in ["voc.png","voi.png"]:
        #await ctx.send(file=discord.File(img))

    # Various variants groups + their description from ECDC
    var_heads = [
        [
            "Variants of Concern (VOC)",
            "For these variants, clear evidence is available indicating a significant impact on transmissibility, severity and/or immunity that is likely to have an impact on the epidemiological situation in the EU/EEA. The combined genomic, epidemiological, and in-vitro evidence for these properties invokes at least moderate confidence. In addition, all the criteria for variants of interest and under monitoring outlined below apply."
            ],
        [
            "Variants of interest (VOI)",
            "For these variants, evidence is available on genomic properties, epidemiological evidence or in-vitro evidence that could imply a significant impact on transmissibility, severity and/or immunity, realistically having an impact on the epidemiological situation in the EU/EEA. However, the evidence is still preliminary or is associated with major uncertainty. In addition, all the criteria for variants under monitoring outlined below apply."
            ],
        [
            "Variants under monitoring",
            "These additional variants of SARS-CoV-2 have been detected as signals through epidemic intelligence, rules-based genomic variant screening, or preliminary scientific evidence. There is some indication that they could have properties similar to those of a VOC, but the evidence is weak or has not yet been assessed by ECDC. Variants listed here must be present in at least one outbreak, detected in a community within the EU/EEA, or there must be evidence that there is community transmission of the variant elsewhere in the world."
            ],
        [
            "De-escalated variants",
            "These additional variants of SARS-CoV-2 have been de-escalated based on at least one the following criteria: (1) the variant is no longer circulating, (2) the variant has been circulating for a long time without any impact on the overall epidemiological situation, (3) scientific evidence demonstrates that the variant is not associated with any concerning properties."
            ]
    ]
    for item in list(zip(files,var_heads)):
        await ctx.send("**> {}**".format(item[1][0]))
        await ctx.send("> {}".format(item[1][1]))
        await ctx.send(file=discord.File(item[0]))

# ImportError: dlopen(/Library/Frameworks/Python.framework/Versions/3.9/lib/python3.9/site-packages/PIL/_imaging.cpython-39-darwin.so, 2): Symbol not found: _clock_gettime
# probably needs newer OS
# def trim(source_filepath, target_filepath=None, background=None):
#     if not target_filepath:
#         target_filepath = source_filepath
#     img = Image.open(source_filepath)
#     if background is None:
#         background = img.getpixel((0, 0))
#     border = Image.new(img.mode, img.size, background)
#     diff = ImageChops.difference(img, border)
#     bbox = diff.getbbox()
#     img = img.crop(bbox) if bbox else img
#     img.save(target_filepath)

bot.run(TOKEN)
