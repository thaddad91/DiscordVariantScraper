#!/usr/bin/env python3

# Author:       Thierry Haddad
# Date:         05-08-2021 (dd/mm/yyyy)
# Description:  First attempt at a Discord bot to scrape and parse 
#               relative variant frequencies that are submitted to GISAID.
#               All data belongs to their respective GISAID uploaders.
# To-do:
# - serialize scraping data to file for saving
# - wrapper for scrape/parse?
# - make up my mind about output formatting...

from discord.ext import commands
import requests, re, json
import country_converter as coco

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
    await ctx.send("> GISAID has been scraped. :white_check_mark:")

# parse scraped data to Discord
@bot.command()   
async def parse(ctx):
    global variants, countries, var_perc
    discl1 = "**> DISCLAIMER**"
    discl2 = "> This bot scrapes the relative percentages of genome **submissions of the past 4 weeks** from the tracked variants to GISAID."
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

bot.run(TOKEN)
