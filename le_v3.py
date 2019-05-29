#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct  8 11:27:31 2018

@author: robertgrant
"""


from databaker.framework import *
import pandas as pd
from databakerUtils.writers import v4Writer
import re, requests, json

inputfile1 = 'data201315.xls'
inputfile2 = 'data201416.xls'
inputfile3 = 'data201517.xlsx'
outputfile ='v4_le.csv'

#these names may change
tabsWeWant1 = ['HE at birth - Males', 'HE at birth - Females', 'HE at age 65 - Males', 'HE at age 65 - Females']
tabs1 = loadxlstabs(inputfile1, tabsWeWant1)

tabsWeWant2 = ['HE - male at birth', 'HE - female at birth', 'HE - male at 65', 'HE - females at 65']
tabs2 = loadxlstabs(inputfile2, tabsWeWant2)

tabsWeWant3 = ['HE - Male at birth', 'HE - Female at birth', 'HE - Male at age 65', 'HE - Female at age 65']
tabs3 = loadxlstabs(inputfile3, tabsWeWant3)

tabs = tabs1 + tabs2 + tabs3

conversionsegments = []

# for each of the selected tabs....do everything thats indented (in this case we only have 1 tab, but that isn't common so we'll stick with the typical approach)
for tab in tabs:       

    # define a selection of cells as the observations
    le = tab.excel_ref('E6').expand(DOWN)
    hle = tab.excel_ref('I6').expand(DOWN)
    dfle = tab.excel_ref('N6').expand(DOWN)
    
    
    #define which tab this is
    thisTab = tab.excel_ref('A1')
    
    
    
    
    area_codes = tab.excel_ref('A6').expand(DOWN).is_not_blank().is_not_whitespace()
    footnotes = tab.excel_ref('A').filter(contains_string('Footnotes')).expand(DOWN)
    la_1 = tab.excel_ref('B6').expand(DOWN).is_not_blank().is_not_whitespace()
    la_2 = tab.excel_ref('C6').expand(DOWN).is_not_blank().is_not_whitespace()
    la_3 = tab.excel_ref('D6').expand(DOWN).is_not_blank().is_not_whitespace()
    le_lcl = tab.excel_ref('F6').expand(DOWN).is_not_blank().is_not_whitespace()
    hle_lcl = tab.excel_ref('J6').expand(DOWN).is_not_blank().is_not_whitespace()
    dfle_lcl = tab.excel_ref('O6').expand(DOWN).is_not_blank().is_not_whitespace()
    le_ucl = tab.excel_ref('G6').expand(DOWN).is_not_blank().is_not_whitespace()
    hle_ucl = tab.excel_ref('K6').expand(DOWN).is_not_blank().is_not_whitespace()
    dfle_ucl = tab.excel_ref('P6').expand(DOWN).is_not_blank().is_not_whitespace()
    la_full = la_1 | la_2 | la_3
    lcl = le_lcl | hle_lcl | dfle_lcl
    ucl = le_ucl | hle_ucl | dfle_ucl
    area_codes = area_codes - footnotes

   
    
    names = tab.excel_ref('E4').expand(RIGHT)
  
    
    
    dimensions = [
              HDim(area_codes, "mid-year-pop-geography", DIRECTLY, LEFT),
              HDim(names, "lifeexpectancyvariable", DIRECTLY, ABOVE),
              HDim(la_full, "GEOG", DIRECTLY, LEFT),
              HDim(lcl, "lower-confidence-limit", DIRECTLY, RIGHT),
              HDim(ucl, "upper-confidence-limit", DIRECTLY, RIGHT),
              HDim(thisTab, "tab", CLOSEST, ABOVE)
                 ]
    
    obs = le | hle | dfle
    
    conversionsegment = ConversionSegment(tab, dimensions, obs).topandas()# < --- processing
    conversionsegments.append(conversionsegment) # <-- adding result of processing this tab to our list
    
# print it all to csv (this code never changes)
conversionsegments = pd.concat(conversionsegments)

#remove nulls
conversionsegments = conversionsegments.dropna(subset=['labels'])

#reset index
conversionsegments = conversionsegments.reset_index(drop = True)


#add data markings
for i in range(0, len(conversionsegments)):
    if(conversionsegments['OBS'][i] == "" and conversionsegments['DATAMARKER'][i] != ".."):
        conversionsegments['DATAMARKER'][i] = "."
        conversionsegments['lower-confidence-limit'][i] = "."
        conversionsegments['upper-confidence-limit'][i] = "."

#take year
conversionsegments['time'] = ''
conversionsegments['time'] = conversionsegments['tab'].apply(lambda x: x[-9:])
conversionsegments['time'] = conversionsegments['time'].apply(lambda x: x[0:5] + x[7:9])
conversionsegments[TIME] = conversionsegments['time']

#variables

conversionsegments['lifeexpectancyvariable'] = conversionsegments['lifeexpectancyvariable'].replace("HLE","Healthy life expectancy")
conversionsegments['lifeexpectancyvariable'] = conversionsegments['lifeexpectancyvariable'].replace("DfLE","Disability-free life expectancy")
conversionsegments['lifeexpectancyvariable'] = conversionsegments['lifeexpectancyvariable'].replace("LE","Life expectancy")

conversionsegments['life-expectancy-variable'] = conversionsegments['lifeexpectancyvariable'].replace("Healthy life expectancy","healthy-life-expectancy")
conversionsegments['life-expectancy-variable'] = conversionsegments['life-expectancy-variable'].replace("Disability-free life expectancy","disability-free-life-expectancy")
conversionsegments['life-expectancy-variable'] = conversionsegments['life-expectancy-variable'].replace("Life expectancy","life-expectancy")


#check for any blank data
check = pd.crosstab(conversionsegments.GEOG ,conversionsegments.lifeexpectancyvariable)
check['total'] = check['Life expectancy'] +  check['Healthy life expectancy'] + check['Disability-free life expectancy'] 
        

for i in range(0, len(check)):
    if check['total'][i] != 36:
        raise ValueError("Something may wrong in the data.\nCheck the 'check' dataframe.")
    

#clean up tab

#reset index
conversionsegments = conversionsegments.reset_index(drop = True)


#work out cohort, using regex for rogue capital letters
conversionsegments['birthcohort'] = ''
conversionsegments['birth-cohort'] = ''

for i in range(0, len(conversionsegments)):
    if re.search(r' [Mm]ale', conversionsegments['tab'][i]) and re.search('birth', conversionsegments['tab'][i]):
        conversionsegments['birth-cohort'][i] = 'birth-males'
        conversionsegments['birthcohort'][i] = 'Males at birth'
    elif re.search(r'[Ff]emale', conversionsegments['tab'][i]) and re.search('birth', conversionsegments['tab'][i]):
        conversionsegments['birth-cohort'][i] = 'birth-females'
        conversionsegments['birthcohort'][i] = 'Females at birth'
    elif re.search(r' [Mm]ale', conversionsegments['tab'][i]) and re.search('65', conversionsegments['tab'][i]):
        conversionsegments['birth-cohort'][i] = 'age-65-males'
        conversionsegments['birthcohort'][i] = 'Males at age 65'
    elif re.search(r'[Ff]emale', conversionsegments['tab'][i]) and re.search('65', conversionsegments['tab'][i]): 
        conversionsegments['birth-cohort'][i] = 'age-65-females'
        conversionsegments['birthcohort'][i] = 'Females at age 65'
    else: conversionsegments['birthcohort'][i] = False


#remove inner london
conversionsegments = conversionsegments[conversionsegments['GEOG'] != 'Inner London']
conversionsegments = conversionsegments[conversionsegments['GEOG'] != 'Outer London']

#check against codelist

codelist = "https://api.beta.ons.gov.uk/v1/code-lists/admin-geography/editions/one-off/codes"            
response = requests.get(codelist)
codelist_json = response.json()

#get all ids
codes = list()
count = codelist_json['count']

codes = list()
for i in range(0, count):
    codes.append(codelist_json["items"][i]['id'])
    
labels = list()
for i in range(0, count):
    labels.append(codelist_json["items"][i]['label'])    
   
admin_geog = {'codes': codes, 'labels': labels}
admin_geog = pd.DataFrame(data = admin_geog)

#get codelist from df
conversionsegments = conversionsegments.merge(admin_geog, how ='left', left_on='mid-year-pop-geography', right_on='codes')

#v4
v4 = conversionsegments[['OBS', 'lower-confidence-limit', 'upper-confidence-limit', 'DATAMARKER', 'time', TIME, 'codes', 'labels', 'life-expectancy-variable', 'lifeexpectancyvariable', 'birth-cohort', 'birthcohort']]
v4.columns = ['V4_3', 'lower-confidence-limit', 'upper-confidence-limit', 'Data_Marking', 'two-year-intervals', 'time', 'admin-geography', 'geography', 'life-expectancy-variable', 'lifeexpectancyvariable', 'birth-cohort', 'birthcohort']

v4.to_csv(outputfile, index = False) 


                
           


