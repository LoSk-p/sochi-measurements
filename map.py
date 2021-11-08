import folium
import xml.dom.minidom as minidom
import branca
from datetime import datetime, timedelta
from branca.element import MacroElement
from jinja2 import Template

class BindColormap(MacroElement):
    """Binds a colormap to a given layer.

    Parameters
    ----------
    colormap : branca.colormap.ColorMap
        The colormap to bind.
    """
    def __init__(self, layer, colormap):
        super(BindColormap, self).__init__()
        self.layer = layer
        self.colormap = colormap
        self._template = Template(u"""
        {% macro script(this, kwargs) %}
            {{this.colormap.get_name()}}.svg[0][0].style.display = 'block';
            {{this._parent.get_name()}}.on('overlayadd', function (eventLayer) {
                if (eventLayer.layer == {{this.layer.get_name()}}) {
                    {{this.colormap.get_name()}}.svg[0][0].style.display = 'block';
                }});
            {{this._parent.get_name()}}.on('overlayremove', function (eventLayer) {
                if (eventLayer.layer == {{this.layer.get_name()}}) {
                    {{this.colormap.get_name()}}.svg[0][0].style.display = 'none';
                }});
        {% endmacro %}
        """)  # noqa

#####################
# parse geiger data #
#####################

datas = []
data = []
with open("data/02.11_geyger.txt") as f:
    for line in f:
        if line[0] != "S" and len(line) > 1:
            data.append(float(line.split()[1])*0.00812)
        if line[0] == "S":
            datas.append(data)
            data = []

datas = datas[1:-9]
start_data = datetime(2021, 11, 2, 9, 00)
times = []
for data in datas:
    time = [start_data + timedelta(seconds=145*i) for i in range(len(data))]
    times.append(time)
    # print(time)
    start_data = time[-1]

geiger_k = 0.00812

##################
# parse sds data #
##################

sb_datas = []
i = 0
with open("data/02.11.10-16:30_2", "r") as f:
    for line in f:
        if len(line) > 1:
            line = line.split()
            if line[0] == "SDS":
                data = {'i': i, 'PM10': float(line[1]), 'PM2.5': float(line[2])}
            if line[0] == "BME":
                data['temperature'] = float(line[1])
                data['pressure'] = float(line[2])/133.322
                data['humidity'] = float(line[3])
                sb_datas.append(data)
                i += 1

print(f"SDS and BME datas: {sb_datas}")
print(f"len sds and bme datas: {len(sb_datas)}")

#################
# parse xml gps #
#################

points = []
doc = minidom.parse("data/ivan_marsh.xml")
wpts = doc.getElementsByTagName("wpt")
for wpt in wpts:
    point = {}
    point['lat'] = wpt.getAttribute("lat")
    point['lon'] = wpt.getAttribute("lon")
    time = wpt.getElementsByTagName("time")[0]
    point['time'] = time.childNodes[0].data
    if len(wpt.getElementsByTagName("cmt")) > 0:
        name = wpt.getElementsByTagName("cmt")[0]
        point['name'] = name.childNodes[0].data
    else:
        point['name'] = "None"
    points.append(point)

points.insert(0, {'lat': '43.657806', 'lon': '40.316480', 'time': '2021-11-02T10:30:30Z', 'name': 'ШАЛЕ'})
points.insert(7, {'lat': '43.614325', 'lon': '40.325705', 'time': '2021-11-02T10:30:30Z', 'name': 'РАЗВИЛКА2'})
points.insert(8, {'lat': '43.619822', 'lon': '40.312740', 'time': '2021-11-02T10:40:30Z', 'name': 'ВЕРОНИКА2'})
points.insert(9, {'lat': '43.623432', 'lon': '40.311745', 'time': '2021-11-02T10:50:30Z', 'name': 'ЭДЕЛЬВЕЙС2'})

##############
# create map #
##############

map = folium.Map(location=[43.613374, 40.331297], zoom_start = 10)

### geiger ###

geiger_group = folium.FeatureGroup(name='Geiger Count')

datas.pop(1)
datas.pop(1)
times.pop(1)
times.pop(1)
deltas = [25, 6, 9, 10, 11, 15, 10, 15, 14, 6, 17, 6, 9]

i_delta = 0
i = 0
data_points = []
for data in datas:
    for mes in data:
        if i == deltas[i_delta]:
            i = 0
            i_delta += 1
        del_lat = (float(points[i_delta + 1]['lat']) - float(points[i_delta]['lat']))/deltas[i_delta]
        del_lon = (float(points[i_delta + 1]['lon']) - float(points[i_delta]['lon']))/deltas[i_delta]
        data_points.append({'lat': float(points[i_delta]['lat']) + del_lat*i, 'lon': float(points[i_delta]['lon']) + del_lon*i, 'data': mes})
        i += 1

colors = []
colormap = branca.colormap.linear.YlOrRd_09.scale(0, 50*geiger_k)
colormap = colormap.to_step(index=[0, 10*geiger_k, 20*geiger_k, 30*geiger_k, 40*geiger_k, 50*geiger_k, 0.57])
colormap.caption = 'μSv/h (maximum safe dose 0.57 μSv/h)'
print(colormap.colors)
# colormap.add_to(map)
colors_rgb = colormap.colors
for color in colors_rgb:
    color_hex = ('{:X}{:X}{:X}').format(int(color[0]*255), int(color[1]*255), int(color[2]*255))
    colors.append(f"#{color_hex}")

### draw points ###

for point in data_points:
    if point['data'] < 10*geiger_k:
        color = colors[0]
    elif point['data'] < 20*geiger_k:
        color = colors[1]
    elif point['data'] < 30*geiger_k:
        color = colors[2]
    elif point['data'] < 40*geiger_k:
        color = colors[3]
    elif point['data'] < 50*geiger_k:
        color = colors[4]
    else:
        color = colors[5]
    geiger_group.add_child(folium.CircleMarker(location=[point['lat'], point['lon']], 
                        radius=5, popup=f"{round(point['data'], 3)} μSv/h", 
                        color=color, 
                        fill_color=color, 
                        fill_opacity=0.9))
# map.add_child(geiger_group)

### temperature, humidity, pressure, SDS ###

temp_group = folium.FeatureGroup(name='Temperature')
hum_group = folium.FeatureGroup(name='Humidity')
pr_group = folium.FeatureGroup(name='Pressure')
pm_group = folium.FeatureGroup(name='PM')

### temperature color

temp_colors = []
temp_index = [4, 6, 8, 10, 12, 20]
temp_colormap = branca.colormap.linear.YlOrRd_09.scale(temp_index[0], temp_index[-1])
temp_colormap = temp_colormap.to_step(index=temp_index)
temp_colormap.caption = 'Temperature, °C'
colors_rgb = temp_colormap.colors
for color in colors_rgb:
    color_hex = ('{:X}{:X}{:X}').format(int(color[0]*255), int(color[1]*255), int(color[2]*255))
    temp_colors.append(f"#{color_hex}")
temp_colors[-1] = '#800026'
print(f"temp colors {temp_colors}, {colors_rgb}")

### humidity color

hum_colors = []
hum_index = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
hum_colormap = branca.colormap.linear.YlGnBu_09.scale(hum_index[0], hum_index[-1])
hum_colormap = hum_colormap.to_step(index=hum_index)
hum_colormap.caption = 'Humidity, %'
colors_rgb = hum_colormap.colors
for color in colors_rgb:
    color_hex = ('{:X}{:X}{:X}').format(int(color[0]*255), int(color[1]*255), int(color[2]*255))
    hum_colors.append(f"#{color_hex}")

### pressure color

pr_colors = []
pr_index = [520, 540, 560, 580, 600, 620, 640.5, 660, 680]
pr_colormap = branca.colormap.linear.Purples_09.scale(pr_index[0], pr_index[-1])
pr_colormap = pr_colormap.to_step(index=pr_index)
pr_colormap.caption = 'Pressure, mmHg'
colors_rgb = pr_colormap.colors
for color in colors_rgb:
    color_hex = ('{:X}{:X}{:X}').format(int(color[0]*255), int(color[1]*255), int(color[2]*255))
    pr_colors.append(f"#{color_hex}")

### PM color

pm_colors = []
pm_index = [0, 1, 2, 3, 4, 5, 10]
pm_colormap = branca.colormap.linear.Reds_09.scale(pm_index[0], pm_index[-1])
pm_colormap = pm_colormap.to_step(index=pm_index)
pm_colormap.caption = 'PM2.5, pm'
colors_rgb = pm_colormap.colors
for color in colors_rgb:
    color_hex = ('{:X}{:X}{:X}').format(int(color[0]*255), int(color[1]*255), int(color[2]*255))
    pm_colors.append(f"#{color_hex}")

deltas = [12, 8, 6, 7, 11, 18, 8, 10, 6, 10, 18, 17, 9]

i_delta = 0
i = 0
data_points = []
sb_datas = sb_datas[:-49]
for mes in sb_datas:
    if i == deltas[i_delta]:
        i = 0
        i_delta += 1
    del_lat = (float(points[i_delta + 1]['lat']) - float(points[i_delta]['lat']))/deltas[i_delta]
    del_lon = (float(points[i_delta + 1]['lon']) - float(points[i_delta]['lon']))/deltas[i_delta]
    data_points.append({'lat': float(points[i_delta]['lat']) + del_lat*i, 'lon': float(points[i_delta]['lon']) + del_lon*i, 'data': mes})
    i += 1

def choose_color(data, colors, index):
    for i in range(len(index) - 1):
        if data < index[i + 1]:
            return colors[i]

def add_circle(group, color, point):
    group.add_child(folium.CircleMarker(location=[point['lat'], point['lon']], 
                        radius=5, popup=f"""PM10: {round(point['data']['PM10'], 1)} pm, PM2.5: {round(point['data']['PM2.5'], 1)} pm,\n
                                            temperature: {round(point['data']['temperature'], 1)} °C,\n
                                            pressure: {round(point['data']['pressure'], 1)} mmHg,\n
                                            humidity: {round(point['data']['humidity'], 1)} %\n
                                            color: {color}""", 
                        color=color, 
                        fill_color=color, 
                        fill_opacity=0.9))


### draw points ###

for point in data_points:
    temp_color = choose_color(point['data']['temperature'], temp_colors, temp_index)
    hum_color = choose_color(point['data']['humidity'], hum_colors, hum_index)
    pr_color = choose_color(point['data']['pressure'], pr_colors, pr_index)
    pm_color = choose_color(point['data']['PM2.5'], pm_colors, pm_index)

    add_circle(temp_group, temp_color, point)
    add_circle(hum_group, hum_color, point)
    add_circle(pr_group, pr_color, point)
    add_circle(pm_group, pm_color, point)

### add all to map ###

temp_colormap.add_to(map)
hum_colormap.add_to(map)
pr_colormap.add_to(map)
pm_colormap.add_to(map)
colormap.add_to(map)

map.add_child(geiger_group)
map.add_child(temp_group)
map.add_child(hum_group)
map.add_child(pr_group)
map.add_child(pm_group)

map.add_child(folium.map.LayerControl())
map.add_child(BindColormap(temp_group, temp_colormap)).add_child(BindColormap(hum_group, hum_colormap))
map.add_child(BindColormap(pr_group, pr_colormap)).add_child(BindColormap(pm_group, pm_colormap))
map.add_child(BindColormap(geiger_group, colormap))

# map.add_child(folium.LayerControl())

map.save("docs/map.html")