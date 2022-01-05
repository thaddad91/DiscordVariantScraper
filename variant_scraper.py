#!/usr/bin/env python3

# Author:       tch
# Date:         05-08-2021 (dd/mm/yyyy)
# Description:  First attempt at a Discord bot to scrape and parse 
#               relative variant frequencies that are submitted to GISAID.
#               All data belongs to their respective GISAID uploaders.
#               Table data belongs to ECDC.
# To-do:
# - send bot messages to channel instead of direct message
# - command for variant-specific info, with recent papers, news etc.
# - wrapper for scrape/parse

import sys
import discord
from os import EX_CANTCREAT
from discord.ext import commands, tasks
import requests, re, json
import country_converter as coco
import pickle
from lxml import etree
import imgkit
#from requests.api import head
from PIL import Image, ImageChops

# verification token for bot
try:
    with open('variant_token.txt','r') as tokenfile:
        TOKEN = tokenfile.read()
    assert TOKEN != ""
except IOError:
    print("Can't open file.")
    sys.exit(1)
except Exception as e:
    print(e)
    sys.exit(1)

# define command prefix and global vars
bot = commands.Bot(command_prefix='!')

# Channel ID's
ch_vardis = 927216007121092658 # bub - variants-distritbution
ch_covvar = 927214034011422771 # bub - covid-variants

variants = None
countries = None
var_perc = None

# scrape GISAID data
#@bot.command()
#@commands.has_permissions(administrator = True)
@tasks.loop(hours = 24)
async def scrape():
    print("Scraping...")
    global variants, countries, var_perc, ch_vardis
    channel = bot.get_channel(ch_vardis)
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
    countries = {}
    for variant in variants:
        var, descrip = variant
        var_url = pre_url.format(var)
        var_text = requests.get(var_url).text
        if not var_text:
            return
        var_json = json.loads(var_text)
        for i in range(0,len(var_json)):
            country = var_json[i]['country']
            fourwktotal = var_json[i]['numcountrytotal_last4wks']
            if country not in countries.keys():
                countries[country] = fourwktotal
                #countries.append(country)
            if var not in var_perc.keys():
                var_perc[var] = {var_json[i]['country']:var_json[i]['percvui_last4wks']}
            else:
                var_perc[var].update({var_json[i]['country']:var_json[i]['percvui_last4wks']})
        print(str(variant)+" done")
    # save scraped data to file
    print("Saving to file...")
    with open("data.pickle","wb") as f:
        pickle.dump([variants,countries,var_perc], f)
    #await ctx.send("> GISAID has been scraped. :white_check_mark:")
    await channel.purge(limit=1000)
    await channel.send("> GISAID has been scraped. :white_check_mark:")

# parse scraped data to Discord
#@bot.command()
#@commands.has_permissions(administrator = True)
@tasks.loop(hours = 24)
async def parse():
    global variants, countries, var_perc, ch_vardis
    channel = bot.get_channel(ch_vardis)
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
    await channel.purge(limit=1000)
    discl1 = "**> DISCLAIMER**"
    discl2 = "> This bot scrapes the relative percentages of genome **submissions of the past 4 weeks** from the tracked variants to GISAID. The variants are limited to the Variants of Concern and Variants of Interest as listed by the WHO (https://www.who.int/en/activities/tracking-SARS-CoV-2-variants/)."
    discl3 = "> Observed frequencies are subject to sampling and reporting biases and **do not** represent exact prevalence."
    discl4 = "> See https://www.gisaid.org/hcov19-variants/ for more info."
    disclaimers = [discl1,discl2,discl3,discl4]
    #await ctx.send("\n".join(disclaimers))
    await channel.send("\n".join(disclaimers))

    # parse percentages per country, per variant
    for country in countries.keys():
        fourwktotal = countries[country]
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
            sent1 = "**> "+flag_iso+" "+country+"** \t\t 4 week total sequenced: "+fourwktotal
            # zip variants with percentages
            results = list(zip([var[1].split()[0] for var in variants], percs))
            sent2 = "> \t\t\t\t"+"\t".join(["{}: {}".format(
                res[0],res[1]) if float(res[1])<50 
                else "**{}:** **{}**".format(res[0],res[1]) 
                for res in results])
            #await ctx.send(sent1)
            #await ctx.send(sent2)
            await channel.send(sent1)
            await channel.send(sent2)
        else:
            print(country, percs)
    #await ctx.send("> All countries parsed. :white_check_mark:")
    await channel.send("> All countries parsed. :white_check_mark:")

def text(elt):
    return elt.text_content().replace(u'\xa0', u' ')

# Retrieve variant information from the ECDC
#@bot.command()
#@commands.has_permissions(administrator = True)
@tasks.loop(hours = 24)
async def variants_overview():
    global variants, ch_covvar

    channel = bot.get_channel(ch_covvar)
    # Scrape ECDC variant page
    ecdc_page = requests.get("https://www.ecdc.europa.eu/en/covid-19/variants-concern")
    if ecdc_page:
        tree = etree.HTML(ecdc_page.content)

    # Scrape all variant tables from ECDC
    tables = tree.xpath('//table[contains(@class,"GridTable4-Accent61 table table-bordered")]')#'//table[@class="GridTable4-Accent61 table table-bordered table-striped"]')
    files = []
    for i,t in enumerate(tables):
        v = str(etree.tostring(t)).rstrip("'").lstrip("b'").replace('\\n','').replace('\\t','')
        # Add table header style
        v = v.replace('<th>','<th style="border-width:1px;border-style:solid;border-color:#121212;background-color:#00bbea;text-align:left;vertical-align:top;">')
        # Add borders to cells
        v = v.replace('<td>','<td style="border-width:1px;border-style:solid;border-color:#121212;text-align:left;vertical-align:top;">')
        filename = 'voi_{}.png'.format(i)
        files.append(filename)
        imgkit.from_string(v,filename)
        trim(filename)

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
    await channel.purge(limit=1000)
    await channel.send("**> Please see https://www.ecdc.europa.eu/en/covid-19/variants-concern for details**")
    # Send image per variant group
    for item in list(zip(files,var_heads)):
        await channel.send("**> {}**".format(item[1][0]))
        await channel.send("> {}".format(item[1][1]))
        await channel.send(file=discord.File(item[0]))

# Copied from user norok2 at https://stackoverflow.com/a/38643741
def trim(source_filepath, target_filepath=None, background=None):
    if not target_filepath:
        target_filepath = source_filepath
    img = Image.open(source_filepath)
    if background is None:
        background = img.getpixel((0, 0))
    border = Image.new(img.mode, img.size, background)
    diff = ImageChops.difference(img, border)
    bbox = diff.getbbox()
    img = img.crop(bbox) if bbox else img
    img.save(target_filepath)

# Shutdown command
# copied from yungmaz13 at https://stackoverflow.com/a/66144295
@bot.command()
@commands.has_permissions(administrator = True)
async def shutdown():
    sys.exit(1)

# Run functions on 24h scheduler
@bot.event
async def on_ready():
    scrape.start()
    parse.start()
    variants_overview.start()
    print('bot is active')

bot.run(TOKEN)