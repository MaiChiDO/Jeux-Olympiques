# Mai Chi DO - 21711316

# Visualisation de donnees sur les Jeux Olympiques
# - Poids en fonction des tailles des athlètes
# - Repartition des médailles Olympiques par pays entre 1896 and 2016

# Modalites d’execution du code: application Bokeh
# utiliser "bokeh serve --show" sur le dossier et non pas sur le fichier main.py pour que le dossier templates puisse
# appliquer les couleurs voulues

import pandas as pd
from pandas import DataFrame
from math import isnan
import json
import numpy as np

from bokeh.plotting import figure, output_file, show
from bokeh.plotting import ColumnDataSource
from bokeh.layouts import row, column
from bokeh.io import curdoc
from bokeh.transform import factor_cmap
from bokeh.palettes import Spectral5
from bokeh.models.widgets import Select, Slider, Tabs, Panel, RadioGroup
from bokeh.models import HoverTool
from bokeh.tile_providers import get_provider, Vendors


#Import des données
df = pd.read_csv('athlete_events.csv')
regions = pd.read_csv('noc_regions.csv')

columns = sorted(df.iloc[:,2:].columns)
discrete = [x for x in columns if df[x].dtype == object]


############ Création du premier graphique (non cartographique) ######################

#Création du widgets
color = Select(title = "Color by:", value='None', options=['None'] + discrete)
min_year = Slider(title="First Year", start=1896, end= 2016, value=1920, step=1, bar_color ='lightpink')
max_year = Slider(title="Last Year", start=1896, end=2016, value=1940, step=1, bar_color ='lightgreen')
nb_points = Slider(start = 0, end = 100, value=50, title = "Percentage of points to display (%)", step = 10, bar_color ='lightblue')

#Définition des functions
def select_athletes():
    selected = df[df.Year.isin(range(min_year.value,max_year.value))].iloc[1:(int(len(df.ID)*nb_points.value/100)+1)]
    return selected

def create_figure1():
    df = select_athletes()
    data = ColumnDataSource(df)

    hover_tool1 = HoverTool(
        tooltips=[
            ( 'Year',   '@Year'),
            ( 'Height',  '@Height'),
            ('Weight', '@Weight')
    ])

    p1 = figure(title = "Relationship between Height and Weight for athletes",x_axis_label = "Height (centimeters)",y_axis_label="Weight (kilograms)",
                height = 600, width = 800)

    c = "#31AADE"
    if color.value != 'None':
        factor = []
        for v in df[color.value]:
            if v not in factor:
                factor.append(v)
        c = factor_cmap(color.value, palette=Spectral5, factors=factor)

    p1.circle(x='Height',y='Weight', source=data, color=c, size=6, hover_color='orange')
    #p.xaxis.axis_line_width = 3
    p1.xaxis.major_label_text_color = "orange"
    p1.yaxis.major_label_text_color = "orange"
    p1.add_tools(hover_tool1)

    return p1

def update(attr, old, new):
    layout1.children[1] = create_figure1()


cont = [min_year, max_year, nb_points, color]
for control in cont:
    control.on_change('value', update)


################ Création d'une cartegraphique dans un nouvel onglet #################

#### Préparation des données du carte ###

#Converts decimal longitude/latitude to Web Mercator format
def coor_wgs84_to_web_mercator(lon, lat):
    k = 6378137
    x = lon * (k * np.pi/180.0)
    y = np.log(np.tan((90 + lat) * np.pi/360.0)) * k
    return (x,y)

#On récupère les noms de pays, les coordonnées des capitales
fp = open("capitals.geojson","r",encoding='utf-8')
capitalsGeojson = json.load(fp)

xyDictionary = {}

#On prépare la construction d’un dictionnaire, en convertissant les coordonnées
for p in capitalsGeojson["features"]:
    #print(p["properties"]["country"])
    X,Y = coor_wgs84_to_web_mercator(p["geometry"]["coordinates"][0],p["geometry"]["coordinates"][1])
    xyDictionary[p["properties"]["country"]] = {}
    xyDictionary[p["properties"]["country"]]["pointx"] = X
    xyDictionary[p["properties"]["country"]]["pointy"] = Y

#On groupe les données initiales par l'identifiant NOC et Medal
df_countries = df.groupby(['NOC','Medal']).size().reset_index(name='counts')

#On prépare la construction d’un ColumnDataFrame qui est utilisé pour créer la carte
listCountries = []

for countryNOC in np.unique(df_countries.NOC):
    country = {}
    df_country = df_countries[df_countries.NOC == countryNOC]

    medals = ['Gold', 'Silver', 'Bronze']
    for med in medals:
        if len(df_country[df_country["Medal"] == med]) > 0:
            country[med] = df_country[df_country["Medal"] == med]['counts'].values[0]
        else :
            country[med] = 0

    if countryNOC == "SGP": countryNOC = "SIN" # Corrige la difference entre les databases
    # country["Country"] = countryNOC
    country["Country"] = regions[regions["NOC"] == countryNOC]['region'].values[0]
    if country["Country"] == "Curacao": country["Country"] = "Netherlands Antilles"
    if country["Country"] in xyDictionary.keys() :
        country["pointx"] = xyDictionary[country["Country"]]["pointx"]
        country["pointy"] = xyDictionary[country["Country"]]["pointy"]

    listCountries.append(country)

df2 = DataFrame(listCountries)
source = ColumnDataSource(df2)

#Création la cartographique
p2 = figure(x_axis_type="mercator", y_axis_type="mercator", active_scroll="wheel_zoom", title="Global repartition of Olympic medals between 1896 and 2016",
            height = 600, width = 900)
tile_provider = get_provider(Vendors.CARTODBPOSITRON)
p2.add_tile(tile_provider)

taille = df2['Gold'].apply(lambda x: x*0.05 if x>0 else 0)
source.add(taille,"taille")

l = ['orange']*len(df2)
source.add(l,"couleur")
p2.circle('pointx','pointy',size='taille',source=source,color="couleur", line_color = 'white', hover_color = 'grey')

#Outil de survol
hover_tool2 = HoverTool(tooltips=[( 'Country',   '@Country'),
                                  ('Gold','@Gold'),
                                  ('Silver','@Silver'),
                                  ('Bronze','@Bronze')])
p2.add_tools(hover_tool2)

#Création le Bouton radio dans le second onglet
bouton_radio = RadioGroup(labels=["Gold", "Silver","Bronze"], active = 0)

#Définition de la callback function
def callback_radio(new):
    couleurs=['orange','green','blue']
    valeurs =['Gold','Silver','Bronze']
    couleur = couleurs[bouton_radio.active]
    val = valeurs[bouton_radio.active]
    colors = [couleur]*len(df2)
    taille = df2[val].apply(lambda x: x*0.05 if x>0 else 0)
    new_data = dict(couleur=colors,taille=taille)
    source.data.update(new_data)


bouton_radio.on_click(callback_radio)

######## Préparation des onglets ########
controls1 = column(min_year, max_year, nb_points, color)
layout1 = row(controls1, create_figure1())
layout2 = row(children=[bouton_radio,p2],sizing_mode = "scale_height")

tab1 = Panel(child=layout1,title="Height vs Weight")
tab2 = Panel(child=layout2,title="Cartography")
tabs = Tabs(tabs=[ tab1, tab2 ], background="darkorange")
curdoc().theme = 'dark_minimal'
curdoc().add_root(tabs)

