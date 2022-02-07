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
from bokeh.models import Button, Toggle, CategoricalColorMapper, ColumnDataSource, TableColumn, DataTable, HoverTool, Label, SingleIntervalTicker, Slider, Spacer, GlyphRenderer, DatetimeTickFormatter, DateRangeSlider, DataRange1d, Range1d, DateSlider, LinearColorMapper, Div, CustomJS, Band, HTMLTemplateFormatter, StringFormatter
from bokeh.palettes import Inferno256, Magma256, Turbo256, Plasma256, Cividis256, Viridis256, OrRd
from bokeh.plotting import figure
from bokeh.events import DocumentReady

# import configuration variables
from config import *

# utility functions

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

# create a data source based on dates
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

# generate the labels for the age stratified plots
def make_age_labels ( nr_labels, nr_series ):

    labels = []
    for j in range(0, nr_series):
        if j == nr_series - 1:
            labels.append('>= ' + str(j*10))
        else:
            labels.append(str(j*10) + '-' + str((j+1)*10-1))

    return labels

# create the map plot, using Pandas-Bokeh
def make_map_plot( data ):

    hover_string = [ ('County', '@NAME_2'), ('Incidence', '@incidence'), ]

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
                             hovertool_string=hover_string, legend=False, figsize=(MAP_WIDTH, MAP_HEIGHT), simplify_shapes=MAP_RESOLUTION, tile_provider=MAP_TILE_PROVIDER)

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

# set properties common to all the plots based on linear xaxis
def set_plot_details ( aplot, xlabel = PLOT_X_LABEL, ylabel = PLOT_Y_LABEL, xtooltip_format = "@x{0}", ytooltip_format = "@y{0}", tooltip_mode ='vline', show_x_label = True, show_y_label = False, ylabel2 = PLOT_Y_LABEL, ytooltip_format2 = None, tooltip_line = None, show_x_axis = True, ylabel3 = PLOT_Y_LABEL, ytooltip_format3 = None ):
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

    # same for 3rd
    if ytooltip_format3:
        tooltip_list.append( (ylabel3, ytooltip_format3) )

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

    aplot.legend.label_text_font_size = PLOT_LEGEND_FONT_SIZE
    aplot.legend.spacing = PLOT_LEGEND_SPACING

def set_plot_date_details( aplot, date_series, length,  asource = None ):

    aplot.xaxis.formatter = DatetimeTickFormatter( months=["%b %Y"], years =["%b %Y"], )

    aplot.x_range.start = date_series[0]        - datetime(1970, 1, 1).date()
    aplot.x_range.end   = date_series[length-1] - datetime(1970, 1, 1).date()

    aplot.xaxis.major_label_orientation = math.pi/4

    if asource:
        y_min, y_max = get_y_limits (asource, date_series[0+DATE_IGNORE], date_series[length-1])
        range_delta = y_max * PLOT_RANGE_FACTOR

        # this thing alone prevents an interference from toggling the visibility of clines
        # and the scale of the plots; comment this line and you will see :-)
        # reference:
        # https://discourse.bokeh.org/t/autoscaling-of-axis-range-with-streaming-multiline-plot-with-bokeh-server/1284/2?u=comperem
        aplot.y_range=Range1d(y_min - range_delta , y_max + range_delta)

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

# calculate a value range adapted to the values present in the date range
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

