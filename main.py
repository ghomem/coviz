import math
import numpy as np
import pandas as pd
import geopandas as gpd
import pandas_bokeh
from pandas_bokeh.geoplot import convert_geoDataFrame_to_patches

from functools import partial
from datetime import datetime
from bokeh.io import curdoc
from bokeh.layouts import layout,gridplot, column, row
from bokeh.models import Button, Toggle, CategoricalColorMapper, ColumnDataSource, HoverTool, Label, SingleIntervalTicker, Slider, Spacer, GlyphRenderer, DatetimeTickFormatter, DateRangeSlider, DataRange1d, Range1d, DateSlider, LinearColorMapper, Div
from bokeh.palettes import Inferno256, Magma256, Turbo256, Plasma256, Cividis256, Viridis256, OrRd
from bokeh.plotting import figure

from .data import process_data, process_data_counties

PAGE_TITLE = 'Coviz'

PLOT_TOOLS    ='save,reset,pan,wheel_zoom,box_zoom'

PLOT_HEIGHT   = 250 # first section, but the actual height is constrained by the width
PLOT_WIDTH    = 400
PLOT_HEIGHT2  = 145 # for the second section
TEXT_WIDTH    = 300
LMARGIN_WIDTH = 20

PLOT_LINE_WIDTH          = 3
PLOT_LINE_WIDTH_CRITICAL = 2

PLOT_LINE_ALPHA       = 0.6
PLOT_LINE_ALPHA_MUTED = 0.1

# for dynamic range adjustments
PLOT_RANGE_FACTOR = 0.05

PLOT_X_LABEL  = 'Days'
PLOT_Y_LABEL  = 'Count'
PLOT_Y_LABEL2 = 'Value'

PLOT_LINE_COLOR           = 'gray'
PLOT_LINE_COLOR_HIGHLIGHT = 'orange'
PLOT_LINE_COLOR_REFERENCE = 'black'
PLOT_LINE_COLOR_CRITICAL  = 'red'

PLOT_LINE_COLOR_PALETTE = Plasma256

PLOT_LEGEND_FONT_SIZE  = '12px'
PLOT_LEGEND_FONT_SIZE2 = '12px'

PLOT_LEGEND_SPACING = 0

PLOT1_TITLE  ='14 Day incidence'
PLOT2_TITLE  ='PCR Positivity'
PLOT3_TITLE  ='Hospitalized'
PLOT4_TITLE  ='Case fatality rate'
PLOT5_TITLE  ='New cases'
PLOT6_TITLE  ='Covid deaths'
PLOT7_TITLE  ='Mortality'
PLOT8_TITLE  ='Rt'
PLOT9_TITLE  ='New cases by age group (click on the legend to hide/show series)'
PLOT10_TITLE ='Covid deaths by age group (click on the legend to hide/show series)'
PLOT11_TITLE ='CFR by age group (click on the legend to hide/show series)'
PLOT12_TITLE ='Vaccination'

CLINES_LABEL = 'Show limits'
CLINES_SWITCH_WIDTH = 140
CLINES_SWITCH_HEIGHT = 30

# epidemic management red lines

INCIDENCE_LIMIT  = 120
POSITIVITY_LIMIT = 4
UCI_LIMIT        = 245
RT_LIMIT         = 1

DATE_IGNORE = 15

# map related

MAP_INCIDENCE_MIN = 0
MAP_INCIDENCE_MAX = 1600
MAP_INCIDENCE_RESOLUTION = 9 # min 3, max 9

MAP_WIDTH  = 500
MAP_HEIGHT = 662

# in meters, eg, 1000 -> 1km
MAP_RESOLUTION = 1500

MAP_TILE_PROVIDER = None #

MAP_TITLE ='14 day Incidence per county'

TEXT_NOTES  ='<strong>Important:</strong> use the mouse for the initial selection and the cursors for fine tuning. The plot takes a couple of seconds to update after each data selection.'

def make_age_labels ( nr_labels ):

    labels = []
    for j in range(0, nr_labels):
        if j == len(data_strat_new) - 1:
            labels.append('>= ' + str(j*10))
        else:
            labels.append(str(j*10) + '-' + str((j+1)*10-1))

    return labels

def make_plot( name, title, range, x_axis_type = 'auto' ):
    return figure(plot_height=PLOT_HEIGHT, plot_width=PLOT_WIDTH, title=title, tools=PLOT_TOOLS, x_range=[0, range], name=name, x_axis_type = x_axis_type)

# because there are several ways to achieve this, let's encapsulate
def make_data_source ( datax, datay ):
    return ColumnDataSource(data=dict(x=datax, y=datay))

def make_data_source2 ( datax, datay, datay2 ):
    return ColumnDataSource(data=dict(x=datax, y=datay, y2=datay2))

# receives a list of lists on for y0, y1, y2, ....
def make_data_source_multi ( datax, datay_list ):

    length = len(datay_list)
    data_dict = {}
    data_dict['x'] = datax
    for j in range(0, length):
        key = 'y' + str(j)
        data_dict[key] = datay_list[j]

    return data_dict

def make_data_source_dates ( dates, datay, datay2 = None ):

    if datay2:
        df = pd.DataFrame(data={ 'x': dates, 'y': datay, 'y2': datay2 }, columns=['x', 'y', 'y2'])
    else:
        df = pd.DataFrame(data={ 'x': dates, 'y': datay }, columns=['x', 'y'])

    return ColumnDataSource(df)

# receives a list of lists on for y0, y1, y2, ....
def make_data_source_multi_dates ( datax, datay_list ):

    length = len(datay_list)
    columns = []
    data_dict = {}
    data_dict['x'] = datax
    columns.append('x')
    for j in range(0, length):
        key = 'y' + str(j)
        data_dict[key] = datay_list[j]
        columns.append(key)

    df = pd.DataFrame(data=data_dict, columns=columns)

    return ColumnDataSource(df)

# set properties common to all the plots based on linear xaxis
def set_plot_details ( aplot, xlabel = PLOT_X_LABEL, ylabel = PLOT_Y_LABEL, xtooltip_format = "@x{0}", ytooltip_format = "@y{0}", tooltip_mode ='vline', show_x_label = True, show_y_label = False, ylabel2 = PLOT_Y_LABEL, ytooltip_format2 = None, tooltip_line = None, show_x_axis = True ):
    aplot.toolbar.active_drag    = None
    aplot.toolbar.active_scroll  = None
    aplot.toolbar.active_tap     = None

    # add the hover tool
    tooltip_attachment = 'left'
    tooltip_list = [ (xlabel, xtooltip_format), (ylabel, ytooltip_format), ]
    tooltip_formatters = {'@x': 'datetime'}

    # check if we have a second line for tooltips
    if ytooltip_format2:
        tooltip_list.append( (ylabel2, ytooltip_format2) )

    # we pass a single render to anchor the tooltip to a specific line
    if tooltip_line:
        ahover = HoverTool(tooltips=tooltip_list, mode=tooltip_mode, attachment=tooltip_attachment, formatters=tooltip_formatters, renderers = [ tooltip_line ])
    else:
        rlist  = aplot.select(dict(type=GlyphRenderer))
        if len(rlist) > 0:
            ahover = HoverTool(tooltips=tooltip_list, mode=tooltip_mode, attachment=tooltip_attachment, formatters=tooltip_formatters, renderers = [ rlist[0] ])
        else:
            # this only happens if we have a plot that has not lines yet, but it is here to prevent a crash
            print('This is probably a plot with no line')
            ahover = HoverTool(tooltips=tooltip_list, mode=tooltip_mode, attachment=tooltip_attachment, )

    ahover.point_policy='snap_to_data'
    ahover.line_policy='nearest'
    aplot.add_tools(ahover)
    aplot.toolbar.active_inspect = ahover

    # control placement / visibility of toolbar
    aplot.toolbar_location = None

    # labels
    if show_x_label:
        aplot.xaxis.axis_label = xlabel
    if show_y_label:
        aplot.yaxis.axis_label = ylabel

    aplot.xaxis.visible = show_x_axis

# set properties common to all the plots with multiple lines
def set_plot_details_multi ( aplot, xlabel = PLOT_X_LABEL, ylabels = [], xtooltip_format = "@x{0}", tooltip_mode ='vline', tooltip_line = None, extra_precision = False, show_x_axis = False ):
    aplot.toolbar.active_drag    = None
    aplot.toolbar.active_scroll  = None
    aplot.toolbar.active_tap     = None

    # add the hover tool
    tooltip_attachment = 'left'
    tooltip_list = [ (xlabel, xtooltip_format) ]
    tooltip_formatters = {'@x': 'datetime'}

    nr_series = len(ylabels)
    j = 0
    for label in ylabels:
        if extra_precision:
            ytooltip_format = "@y"+str(j)+"{0.00}"
        else:
            ytooltip_format = "@y"+str(j)+"{0}"
        j = j + 1
        tooltip_list.append( (label, ytooltip_format ) )

    # we pass a single render to anchor the tooltip to a specific line
    if tooltip_line:
        ahover = HoverTool(tooltips=tooltip_list, mode=tooltip_mode, attachment=tooltip_attachment, formatters=tooltip_formatters, renderers = [ tooltip_line ])
    else:
        rlist  = aplot.select(dict(type=GlyphRenderer))
        if len(rlist) > 0:
            ahover = HoverTool(tooltips=tooltip_list, mode=tooltip_mode, attachment=tooltip_attachment, formatters=tooltip_formatters, renderers = [ rlist[0] ])
        else:
            # this only happens if we have a plot that has not lines yet, but it is here to prevent a crash
            print('This is probably a plot with no line')
            ahover = HoverTool(tooltips=tooltip_list, mode=tooltip_mode, attachment=tooltip_attachment, )

    ahover.point_policy='snap_to_data'
    ahover.line_policy='nearest'
    aplot.add_tools(ahover)
    aplot.toolbar.active_inspect = ahover

    # control placement / visibility of toolbar
    aplot.toolbar_location = None

    # labels
    #aplot.xaxis.axis_label = xlabel
    aplot.xaxis.visible = show_x_axis

    aplot.legend.location = 'top_left'
    aplot.legend.click_policy = 'mute'

    aplot.legend.label_text_font_size = PLOT_LEGEND_FONT_SIZE2
    aplot.legend.spacing = PLOT_LEGEND_SPACING

def set_plot_date_details( aplot, asource = None ):

    aplot.xaxis.formatter = DatetimeTickFormatter( months=["%b %Y"], years =["%b %Y"], )

    aplot.x_range.start = data_dates[0] - datetime(1970, 1, 1).date()
    aplot.x_range.end   = data_dates[days-1] - datetime(1970, 1, 1).date()

    aplot.xaxis.major_label_orientation = math.pi/4

    if asource:
        y_min, y_max = get_y_limits (asource, data_dates[0+DATE_IGNORE], data_dates[days-1])
        range_delta = y_max * PLOT_RANGE_FACTOR

        # this thing alone prevents an interference from toggling the visibility of clines
        # and the scale of the plots; comment this line and you will see :-)
        # reference:
        # https://discourse.bokeh.org/t/autoscaling-of-axis-range-with-streaming-multiline-plot-with-bokeh-server/1284/2?u=comperem
        aplot.y_range=Range1d(y_min - range_delta , y_max + range_delta)

def make_map_plot( data ):

    plot_map_hover = [ ('County', '@NAME_2'), ('Incidence', '@incidence'), ]

    # According to the docs the colormap parameter of the plot_bokeh function:
    # "Defines the colors to plot. Can be either a list of colors or the name of a Bokeh color palette"

    # because our original palette has the colors in the wrong direction
    # and because of this https://github.com/bokeh/bokeh/issues/7297
    # we can't just invert the colormap_range or we loose the legend on the color bar
    # so we we are forced to reverse the palette manually

    colormap = reverse_palette(OrRd)[MAP_INCIDENCE_RESOLUTION]

    # we now create a plot based on a geodataframe to which an incidence column has been added
    # https://patrikhlobil.github.io/Pandas-Bokeh/#geoplots
    aplot = data.plot_bokeh( name = 'themap', title=MAP_TITLE, category='incidence', hovertool=True, colormap=colormap, colormap_range=(MAP_INCIDENCE_MIN, MAP_INCIDENCE_MAX),
                             hovertool_string=plot_map_hover, legend=False, figsize=(MAP_WIDTH, MAP_HEIGHT), simplify_shapes=MAP_RESOLUTION, tile_provider=MAP_TILE_PROVIDER)

    # we are selecting the plot by name and then getting the data_source
    # the name was given in the invocatino of plot_bokeh
    data_source = aplot.select(name = 'themap').data_source

    # remove the interactions and decorations
    aplot.toolbar.active_drag   = None
    aplot.toolbar.active_scroll = None
    aplot.toolbar.active_tap    = None

    aplot.toolbar_location = None

    aplot.xaxis.visible = False
    aplot.yaxis.visible = False

    return aplot, data_source

# this function iterates across the several resolutions (color sets) of a bokeh palette
# and reverses their order
def reverse_palette ( original_palette ):

    palette = { }
    base_value = 3
    for item in original_palette.items():
        #print(base_value, item)
        palette[base_value] = item[1][::-1]
        base_value = base_value + 1

    return palette

# callbacks

# for the toggle button action
def update_state(new):

    cline1.visible = clines_switch.active
    cline2.visible = clines_switch.active
    cline3.visible = clines_switch.active
    cline4.visible = clines_switch.active

# for the data range
def update_plot_range (attr, old, new, section):

    if section == '1':
        my_slider    = date_slider1
        my_plot_data = plot_data_s1
    else:
        my_slider    = date_slider2
        my_plot_data = plot_data_s2

    date_i = my_slider.value[0]
    date_f = my_slider.value[1]

    if date_i == date_f:
        return

    date_i_cmp = my_slider.value_as_date[0]
    date_f_cmp = my_slider.value_as_date[1]

    for d in my_plot_data:

        # we get the plot from the tuple
        p = d[0]

        # for some reason we need to pad the range to get an exact day match with the slider
        p.x_range.start = date_i - pd.Timedelta(days=1).total_seconds()*1000

        # this one is just for the line not to be attached to the limit of the plot
        p.x_range.end   = date_f + pd.Timedelta(days=2).total_seconds()*1000

        # we pass the data source from the tuple
        y_min, y_max = get_y_limits (d[1], date_i_cmp, date_f_cmp)
        if math.isnan(y_min) or math.isnan(y_max):
            print('not rescaling due to having received nan')
            continue

        #print (y_min, y_max)

        # adjust range
        range_delta = y_max * PLOT_RANGE_FACTOR
        p.y_range.end    = y_max + range_delta
        p.y_range.start  = y_min - range_delta

# for the map
def update_map(attr, old, new):

    date = date_slider_map.value_as_date

    print('map updating', date)

    #print('process data counties - START')

    new_data_incidence_counties, xxx, yyy = process_data_counties( date )

    #print('process data counties - DONE')

    #print('make new map - START')

    # index in tmp_df has repeat values, as multipoly in the original data were converted into several lines
    j = 0
    inc_list = np.array ( [] )
    for index in aux_index:
        #print (index, j)
        inc_list = np.append(inc_list, new_data_incidence_counties['incidence'][index])
        j = j + 1

    plot_map_s1.data['Colormap'] = inc_list

    #print('make new map - DONE')

def get_y_limits ( source, date_i, date_f ):

    # calculate indexes in the y data
    y_i = np.where( source.data['x'] == date_i )[0][0]
    y_f = np.where( source.data['x'] == date_f )[0][0]

    # get min and max iterating over the plot series
    y_max_list = []
    y_min_list = []
    for s in source.data:
        # x and index are also sries in the data source, let's ignore them
        if s == 'x' or s == 'index':
            continue
        y_max_list.append( np.nanmax(source.data[s][y_i:y_f]) )
        y_min_list.append( np.nanmin(source.data[s][y_i:y_f]) )

    # return the minimum of the minimuns for the interval, same for maximum
    return min(y_min_list), max(y_max_list)

# main

curdoc().title = PAGE_TITLE

# fetch data from files

# regular plots data
data_dates, data_new, data_hosp, data_hosp_uci, data_cv19_deaths, data_incidence, data_cfr, data_rt, data_pcr_pos, data_total_deaths, data_avg_deaths, data_strat_new, data_strat_cv19_deaths, data_strat_cfr, data_vacc_part, data_vacc_full = process_data()

# map data
data_incidence_counties, map_date_i, map_date_f  = process_data_counties()

# needs to be converted for index extraction, this is what plot_bokeh does inside
aux_df = convert_geoDataFrame_to_patches(data_incidence_counties, 'geometry')

# the conversion transforms lines that have multiple polygons into multiple lines with the same index
# index has repeat values because of that
aux_index = aux_df.index

# calculate the nr of days using the most reliable source

days=len(data_new)

plot_data_s1 = []
plot_data_s2 = []

#### First page ####

# one

source_plot1 = make_data_source_dates(data_dates, data_incidence)
plot1 = make_plot ('incidence', PLOT1_TITLE, days, 'datetime')
l11 = plot1.line('x','y', source=source_plot1, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )
set_plot_details(plot1, 'Date', 'Count', '@x{%F}', '@y{0.00}', 'vline', False, False)
set_plot_date_details(plot1, source_plot1)

plot_data_s1.append( (plot1, source_plot1) )

# two

source_plot2 = make_data_source_dates(data_dates, data_pcr_pos)
plot2 = make_plot ('pcr_pos', PLOT2_TITLE, days, 'datetime')
l21 = plot2.line('x', 'y', source=source_plot2, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )
set_plot_details(plot2, 'Date', '%', '@x{%F}', '@y{0.00}', 'vline', False, False)
set_plot_date_details(plot2, source_plot2)

plot_data_s1.append( (plot2, source_plot2) )

# three

source_plot3 = make_data_source_dates(data_dates, data_hosp, data_hosp_uci)
plot3 = make_plot ('hosp', PLOT3_TITLE, days, 'datetime')
l31 = plot3.line('x', 'y',  source=source_plot3, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, legend_label='Total' )
l32 = plot3.line('x', 'y2', source=source_plot3, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR_HIGHLIGHT, legend_label='UCI' )

plot3.legend.location = 'top_left'
set_plot_details(plot3, 'Date', 'Total', '@x{%F}', '@y{0}', 'vline', False, False,'UCI', "@y2{0}", l31)
set_plot_date_details(plot3, source_plot3)

plot3.legend.label_text_font_size = PLOT_LEGEND_FONT_SIZE

plot_data_s1.append( (plot3, source_plot3) )

# four

source_plot4 = make_data_source_dates(data_dates, data_cfr)
plot4 = make_plot ('cfr', PLOT4_TITLE, days, 'datetime')
plot4.line('x', 'y', source=source_plot4, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )
set_plot_details(plot4, 'Date', '%', '@x{%F}', '@y{0.00}', 'vline', False, False)
set_plot_date_details(plot4)

plot_data_s1.append( (plot4, source_plot4) )

# five

source_plot5 = make_data_source_dates(data_dates, data_new)
plot5 = make_plot ('new', PLOT5_TITLE, days, 'datetime')
plot5.line('x', 'y', source=source_plot5, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )
set_plot_details(plot5, 'Date', 'Count', '@x{%F}', '@y{0}', 'vline', False, False)
set_plot_date_details(plot5, source_plot5)

plot_data_s1.append( (plot5, source_plot5) )

# six

source_plot6 = make_data_source_dates(data_dates, data_rt)
plot6 = make_plot ('rt', PLOT8_TITLE, days, 'datetime')
plot6.line('x', 'y', source=source_plot6, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR,  )
set_plot_details(plot6, 'Date', 'Value', '@x{%F}', '@y{0.00}', 'vline', False, False)
set_plot_date_details(plot6, source_plot6)

plot_data_s1.append( (plot6, source_plot6) )

# seven

source_plot7 = make_data_source_dates(data_dates, data_total_deaths, data_avg_deaths)
plot7 = make_plot ('total deaths', PLOT7_TITLE, days, 'datetime')
l71 = plot7.line('x', 'y',  source=source_plot7, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, legend_label='Current' )
l72 = plot7.line('x', 'y2', source=source_plot7, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR_REFERENCE, legend_label='2015-2019' )

plot7.legend.location = 'top_left'
set_plot_details(plot7, 'Date', 'Current', '@x{%F}', '@y{0}', 'vline', False, False,'2015-2019', "@y2{0}", l71)
set_plot_date_details(plot7, source_plot7)

plot7.legend.label_text_font_size = PLOT_LEGEND_FONT_SIZE

plot_data_s1.append( (plot7, source_plot7) )

# eight

source_plot8 = make_data_source_dates(data_dates, data_cv19_deaths)
plot8 = make_plot ('deaths', PLOT6_TITLE, days, 'datetime')
plot8.line('x', 'y', source=source_plot8, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR,  )
set_plot_details(plot8, 'Date', 'Count', '@x{%F}', '@y{0}', 'vline', False, False)
set_plot_date_details(plot8, source_plot8)

plot_data_s1.append( (plot8, source_plot8) )

# Critical lines
# default, primary, success, warning, danger, light
clines_switch = Toggle(label=CLINES_LABEL, button_type='default', align='end', width=CLINES_SWITCH_WIDTH, height=CLINES_SWITCH_HEIGHT, name = 'section1_button')
clines_switch.on_click(update_state)

source_plot1_critical = make_data_source_dates(data_dates, np.full( days, INCIDENCE_LIMIT ))
source_plot2_critical = make_data_source_dates(data_dates, np.full( days, POSITIVITY_LIMIT ))
source_plot3_critical = make_data_source_dates(data_dates, np.full( days, UCI_LIMIT ))
source_plot6_critical = make_data_source_dates(data_dates, np.full( days, RT_LIMIT ))

# critical lines
cline1 = plot1.line('x', 'y', source=source_plot1_critical, line_width=PLOT_LINE_WIDTH_CRITICAL, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR_CRITICAL)
cline2 = plot2.line('x', 'y', source=source_plot2_critical, line_width=PLOT_LINE_WIDTH_CRITICAL, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR_CRITICAL)
cline3 = plot3.line('x', 'y', source=source_plot3_critical, line_width=PLOT_LINE_WIDTH_CRITICAL, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR_CRITICAL)
cline4 = plot6.line('x', 'y', source=source_plot6_critical, line_width=PLOT_LINE_WIDTH_CRITICAL, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR_CRITICAL)

cline1.visible = False
cline2.visible = False
cline3.visible = False
cline4.visible = False

# date range widget

# for scale calculation we start later because of the moving average
date_i = data_dates[0+6]
date_f = data_dates[days-1]

date_slider1 = DateRangeSlider(title="Date Range: ", start=date_i, end=date_f, value=( date_i, date_f ), step=1)

date_slider1.on_change('value', partial(update_plot_range, section="1"))

#### Second page ####

nr_series = len(data_strat_new)
labels = make_age_labels(nr_series)
palette = PLOT_LINE_COLOR_PALETTE

# spacing the color as much as possible
color_multiplier = math.floor(256 / nr_series + 1)

# nine

source_plot9 = make_data_source_multi_dates (data_dates, data_strat_new)
plot9 = make_plot ('plot9', PLOT9_TITLE, days, 'datetime')

lines = []
for j in range(0, nr_series ):
    lines.append( plot9.line('x', 'y'+str(j), source=source_plot9, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=palette[color_multiplier * j], muted_alpha=PLOT_LINE_ALPHA_MUTED, legend_label=labels[j] ) )

# we know by inspection that line representing 40-49 is on top
set_plot_details_multi(plot9, 'Date', labels, '@x{%F}', 'vline', lines[4], False, False)
set_plot_date_details(plot9, source_plot9)

plot_data_s2.append( (plot9, source_plot9) )

# ten

source_plot10 = make_data_source_multi_dates (data_dates, data_strat_cv19_deaths)
plot10 = make_plot ('plot10', PLOT10_TITLE, days, 'datetime')

lines = []
for j in range(0, nr_series ):
    lines.append( plot10.line('x', 'y'+str(j), source=source_plot10, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=palette[color_multiplier * j], muted_alpha=PLOT_LINE_ALPHA_MUTED, legend_label=labels[j] ) )

# the line for >= 80 is on top for this case
set_plot_details_multi(plot10, 'Date', labels, '@x{%F}', 'vline', lines[nr_series -1 ], False, False)
set_plot_date_details(plot10, source_plot10)

plot_data_s2.append( (plot10, source_plot10) )

# eleven

source_plot11 = make_data_source_multi_dates (data_dates, data_strat_cfr)
plot11 = make_plot ('plot11', PLOT11_TITLE, days, 'datetime')

lines = []
for j in range(0, nr_series ):
    lines.append( plot11.line('x', 'y'+str(j), source=source_plot11, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=palette[color_multiplier * j], muted_alpha=PLOT_LINE_ALPHA_MUTED, legend_label=labels[j] ) )

# the line for >= 80 is on top for this case
set_plot_details_multi(plot11, 'Days', labels, '@x{%F}', 'vline', lines[nr_series -1 ], True, False)
set_plot_date_details(plot11, source_plot11)

plot_data_s2.append( (plot11, source_plot11) )

# twelve

source_plot12 = make_data_source_dates(data_dates, data_vacc_part, data_vacc_full)
plot12 = make_plot ('vaccination', PLOT12_TITLE, days, 'datetime')
l121 = plot12.line('x', 'y',  source=source_plot12, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, legend_label='Partial' )
l122 = plot12.line('x', 'y2', source=source_plot12, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR_HIGHLIGHT, legend_label='Complete' )
plot12.legend.location = 'top_left'
set_plot_details(plot12, 'Date', 'Partial', '@x{%F}', '@y{0}', 'vline', False, False,'Complete', "@y2{0}", l121, False)

set_plot_date_details(plot12, source_plot12)

plot_data_s2.append( (plot12, source_plot12) )

# date range widget

date_slider2 = DateRangeSlider(title="Date Range: ", start=date_i, end=date_f, value=( date_i, date_f ), step=1)

date_slider2.on_change('value', partial(update_plot_range, section="2"))

#### Third page ####

# pandas option, necessary for bokeh plots from pandas
pd.set_option('plotting.backend', 'pandas_bokeh')

plot_map, plot_map_s1  = make_map_plot ( data_incidence_counties )

# the step parameter is in miliseconds
step_days = 7
date_slider_map = DateSlider(title='Selected date', start=map_date_i, end=map_date_f, value=map_date_f, step = step_days*1000*60*60*24, width_policy='fixed', width=PLOT_WIDTH-40 )

date_slider_map.on_change('value_throttled', partial(update_map))

#### Plot layout section ###

# the layout name is added here then invoked from the HTML template
# all roots added here must be invoked on the HTML

# section 1

control_spacer = Spacer(width=10, height=10, width_policy='auto', height_policy='fixed')

controls1 = row (date_slider1, control_spacer, clines_switch, name="section1_controls" )
curdoc().add_root(controls1)

grid = gridplot([ 
                  [ plot1, plot3, plot5, plot7 ],
                  [ plot2, plot4, plot6, plot8 ] ],
                  plot_width=PLOT_WIDTH, plot_height=PLOT_HEIGHT, toolbar_location=None, sizing_mode='scale_width')

layout1 = layout( grid, name='section1', sizing_mode='scale_width')

curdoc().add_root(layout1)

# section 2

controls2 = row (date_slider2, name="section2_controls" )
curdoc().add_root(controls2)

grid2 = gridplot ([
                   [plot9,  plot11],
                   [plot10, plot12] ], 
                   plot_width=PLOT_WIDTH, plot_height=PLOT_HEIGHT2, toolbar_location=None, sizing_mode='scale_width')

layout2 = layout( grid2, name='section2', sizing_mode='scale_width')

curdoc().add_root(layout2)

# section 3

# we create plot identical to plot1 (incidence), using the existing data source
plot1_copy = make_plot ('incidence', PLOT1_TITLE, days, 'datetime')
plot1_copy.line('x','y', source=source_plot1, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )
set_plot_details(plot1_copy, 'Date', 'Count', '@x{%F}', '@y{0.00}', 'vline', False, False)
set_plot_date_details(plot1_copy, source_plot1)

# but we change the range
# we can't do this on a directy copy of plot1, because it is shallow
plot1_copy.x_range.start = pd.to_datetime(map_date_i)
plot1_copy.x_range.end   = pd.to_datetime(map_date_f)

notes = Div(text=TEXT_NOTES, width=TEXT_WIDTH)

# now the layout

slider_spacer = Spacer(width=30, height=50, width_policy='auto', height_policy='fixed')

column_section3_map    = column(plot_map)
column_section3_others = column( [plot1_copy, row( [slider_spacer, date_slider_map] ), row( [ slider_spacer, notes] ) ] )

row_section3 = row ( column_section3_map , column_section3_others )

layout3 = layout( row_section3, name='section3')

curdoc().add_root(layout3)
