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
from bokeh.models import Button, Toggle, CategoricalColorMapper, ColumnDataSource, HoverTool, Label, SingleIntervalTicker, Slider, Spacer, GlyphRenderer, DatetimeTickFormatter, DateRangeSlider, DataRange1d, Range1d, DateSlider, LinearColorMapper, Div, CustomJS, Band
from bokeh.palettes import Inferno256, Magma256, Turbo256, Plasma256, Cividis256, Viridis256, OrRd
from bokeh.plotting import figure
from bokeh.events import DocumentReady

from .data import process_data, process_data_counties

# import configuration variables
from config import *

window_size_data_source = ColumnDataSource( data = { 'width' :[0] ,  'height': [0] } )

# by default we assume the layout is horizontal
current_horizontal = True

# functions

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

#### callbacks ####

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

    print('process data counties - START')

    new_data_incidence_counties, xxx, yyy = process_data_counties( date )

    print('process data counties - DONE')

    # index in aux_index has repeated values, as multipoly rows in the original data were converted into several rows
    j = 0
    inc_list = np.array ( [] )
    for index in aux_index:
        #print (index, j)
        inc_list = np.append(inc_list, new_data_incidence_counties['incidence'][index])
        j = j + 1

    # we update the data source directly on the column that holds the incidence info
    # this column, name Colormap, is added inside plot_bokeh
    plot_map_s1.data['Colormap'] = inc_list

    # we refresh the tooltips using the Colormap column as the list
    plot_map.hover.tooltips = [ ('County', '@NAME_2'), ('Incidence', '@Colormap'), ]

# after document load
def on_document_ready(evt):
    # here we change some property on the fake_toggle widget
    print('document is ready, refreshing fake widget')

    # this forces a change on the fake slider, which then invokes the JS callback
    fake_slider.value = ( date_i, date_i )
    fake_slider.value = ( date_i, date_f )

# this callbacks takes action on the server side upon dimensions change
def on_dimensions_change(attr, old, new):

    width  = new['width'][0]
    height = new['height'][0]

    global current_horizontal

    print('current dimensions', width, height)

    if width >= height and width > MIN_HORIZONTAL_WIDTH:
        print('orientation is horizontal')
        horizontal = True
    else:
        print('orientation is vertical')
        horizontal = False

    if (current_horizontal != horizontal):
        print ('redoing layouts')

        curdoc().clear()

        # adjust the widgets depending on the current orientation
        adjust_widgets_to_layout(horizontal)

        curdoc().add_root(controls1)

        if horizontal:
            curdoc().add_root(layout1_h)
        else:
            curdoc().add_root(layout1_v)

        curdoc().add_root(controls2)

        if horizontal:
            curdoc().add_root(layout2_h)
            curdoc().add_root(layout3_h)
        else:
            curdoc().add_root(layout2_v)
            curdoc().add_root(layout3_v)

        # store the horizontalness state
        current_horizontal = horizontal


dimensions_callback = CustomJS( args=dict(ds=window_size_data_source), code="""
var width, height;
var new_data = {};
height = window.innerHeight || document.documentElement.clientHeight || document.body.clientHeight;
width  = window.innerWidth  || document.documentElement.clientWidth  || document.body.clientWidth;
console.log("Javascript callback", height, width);

// needs to be a list, otherwise we have a server side error
new_data['height'] = [height];
new_data['width' ] = [width];
ds.data = new_data;
ds.change.emit();

""")

#### end of call backs ####

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

def make_layouts( ):

    control_spacer = Spacer(width=10, height=10, width_policy='auto', height_policy='fixed')

    # use this line for debugging with the fake slider
    controls1 = row (date_slider1, control_spacer, fake_slider, clines_switch, name="section1_controls" )

    fake_slider.visible = False

    # first

    grid_h = gridplot([
                      [ plot5, plot3, plot1, plot8 ],
                      [ plot2, plot4, plot6, plot7 ] ],
                      plot_width=PLOT_WIDTH, plot_height=PLOT_HEIGHT, toolbar_location=None, sizing_mode='scale_width')

    grid_v = gridplot([
                      [ plot5, plot3 ],
                      [ plot1, plot8 ],
                      [ plot6, plot7 ],
                      [ plot2, plot4 ] ],
                      plot_width=PLOT_WIDTH, plot_height=PLOT_HEIGHT, toolbar_location=None, sizing_mode='scale_width')

    # second

    controls2 = row (date_slider2, name="section2_controls" )

    grid2_h = gridplot ([
                        [plot9,  plot11],
                        [plot10, plot12] ],
                        plot_width=PLOT_WIDTH, plot_height=PLOT_HEIGHT2, toolbar_location=None, sizing_mode='scale_width')

    grid2_v = gridplot ([
                        [plot9 ],
                        [plot10],
                        [plot11],
                        [plot12] ],
                        plot_width=PLOT_WIDTH, plot_height=PLOT_HEIGHT2, toolbar_location=None, sizing_mode='scale_width')

    # third

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

    layout1_h = layout(grid_h,  name='section1', sizing_mode='scale_width')
    layout2_h = layout(grid2_h, name='section2', sizing_mode='scale_width')

    column_section3_map    = column(plot_map)
    column_section3_others = column( [plot1_copy, row( [slider_spacer, date_slider_map] ), row( [ slider_spacer, notes] ) ] )

    row_section3 = row ( column_section3_map , column_section3_others )
    layout3_h = layout( row_section3, name='section3')

    layout1_v = layout(grid_v,  name='section1', sizing_mode='scale_width')
    layout2_v = layout(grid2_v, name='section2', sizing_mode='scale_width')

    # we don't need the notes text on the vertical layout
    column_section3_map = column( [plot_map, row( [slider_spacer, date_slider_map] ), plot1_copy ] )

    layout3_v = layout( column_section3_map, name='section3')

    return layout1_h, layout2_h, layout3_h, layout1_v, layout2_v, layout3_v, controls1, controls2, plot1_copy

def adjust_widgets_to_layout( horizontal ):

    plot_list   = [ plot1, plot1_map, plot2, plot3, plot4, plot5, plot6, plot7, plot8, plot9, plot10, plot11, plot12, plot_map ]
    plot_list_l = [ plot3, plot7, plot9, plot10, plot11, plot12 ] # these ones have legend

    for p in plot_list:
        if horizontal:
            p.title.text_font_size = TITLE_SIZE_HORIZONTAL_LAYOUT
        else:
            p.title.text_font_size = TITLE_SIZE_VERTICAL_LAYOUT

    for p in plot_list_l:
        if horizontal:
            p.legend.label_text_font_size = PLOT_LEGEND_FONT_SIZE
        else:
            p.legend.label_text_font_size = PLOT_LEGEND_FONT_SIZE_VERTICAL_LAYOUT

    if horizontal:
        plot_map.plot_width   = MAP_WIDTH
        plot_map.plot_height  = MAP_HEIGHT
        plot1_map.width       = PLOT_WIDTH
        plot1_map.height      = PLOT_HEIGHT
        date_slider_map.width = PLOT_WIDTH-40
    else:
        factor = 1.7
        factor2 = 1.91
        plot_map.plot_width   = int(MAP_WIDTH*factor)
        plot_map.plot_height  = int(MAP_HEIGHT*factor)
        plot1_map.width       = int(plot1_map.plot_width*factor2)
        plot1_map.height      = PLOT_HEIGHT
        date_slider_map.width = plot1_map.width-40

# main

curdoc().title = PAGE_TITLE

# fetch data from files

# regular plots data
data_dates, data_new, data_hosp, data_hosp_uci, data_cv19_deaths, data_incidence, data_cfr, data_rt, data_pos, data_total_deaths, data_avg_deaths, data_avg_deaths_inf, data_avg_deaths_sup, data_strat_new, data_strat_cv19_deaths, data_strat_cfr, data_vacc_part, data_vacc_full, data_vacc_boost = process_data()

# map data
data_incidence_counties, map_date_i, map_date_f  = process_data_counties()

# our original data has one line per county, and each line contains a set of polygons
# for a performant map update on update_map we need to keep a converted version
# this version has multiple lines with the same index for counties that hove multipolygons
aux_df = convert_geoDataFrame_to_patches(data_incidence_counties, 'geometry')

# the conversion transforms lines that have multiple polygons into multiple lines with the same index
# index has repeated values because of that
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

source_plot2 = make_data_source_dates(data_dates, data_pos)
plot2 = make_plot ('_pos', PLOT2_TITLE, days, 'datetime')
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

df = pd.DataFrame(data={ 'x': data_dates, 'y': data_total_deaths, 'y2': data_avg_deaths, 'y3': data_avg_deaths_inf, 'y4': data_avg_deaths_sup }, columns=['x', 'y', 'y2', 'y3', 'y4'])
source_plot7 = ColumnDataSource(df)

plot7 = make_plot ('total deaths', PLOT7_TITLE, days, 'datetime')
l71 = plot7.line('x', 'y',  source=source_plot7, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, legend_label='Current' )
l72 = plot7.line('x', 'y2', source=source_plot7, line_width=1, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR_REFERENCE, legend_label='2015-2019 ± SD' )

band = Band(base='x', lower='y3', upper='y4', source=source_plot7, level='underlay', line_width=1, line_color=PLOT_LINE_COLOR_HIGHLIGHT, fill_color=PLOT_LINE_COLOR_HIGHLIGHT, line_alpha=PLOT_LINE_ALPHA, fill_alpha=PLOT_LINE_ALPHA)
plot7.add_layout(band)

plot7.legend.location = 'top_left'
set_plot_details(plot7, 'Date', 'Current', '@x{%F}', '@y{0}', 'vline', False, False,'2015-2019', "@y2{0} (@y3{0}-@y4{0})", l71)
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

df12 = pd.DataFrame(data={ 'x': data_dates, 'y': data_vacc_part, 'y2': data_vacc_full, 'y3': data_vacc_boost }, columns=['x', 'y', 'y2', 'y3'])
source_plot12 = ColumnDataSource(df12)

plot12 = make_plot ('vaccination', PLOT12_TITLE, days, 'datetime')
l121 = plot12.line('x', 'y',  source=source_plot12, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, legend_label='Partial' )
l122 = plot12.line('x', 'y2', source=source_plot12, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR_HIGHLIGHT, legend_label='Complete' )
l122 = plot12.line('x', 'y3', source=source_plot12, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR_REFERENCE, legend_label='Booster' )
plot12.legend.location = 'top_left'
set_plot_details(plot12, 'Date', 'Partial', '@x{%F}', '@y{0}', 'vline', False, False,'Complete', "@y2{0}", l121, False, 'Booster', "@y3{0}")

set_plot_date_details(plot12, source_plot12)

plot_data_s2.append( (plot12, source_plot12) )

# date range widget

date_slider2 = DateRangeSlider(title="Date Range: ", start=date_i, end=date_f, value=( date_i, date_f ), step=1)

date_slider2.on_change('value', partial(update_plot_range, section="2"))

#### Third page ####

# pandas option, necessary for bokeh plots from pandas
pd.set_option('plotting.backend', 'pandas_bokeh')

plot_map, plot_map_s1 = make_map_plot ( data_incidence_counties )

# the step parameter is in miliseconds
step_days = 7
date_slider_map = DateSlider(title='Selected date', start=map_date_i, end=map_date_f, value=map_date_f, step = step_days*1000*60*60*24, width_policy='fixed', width=PLOT_WIDTH-40 )

date_slider_map.on_change('value_throttled', partial(update_map))

#### Plot layout section ###

## handling different layout orientations

# register on_document_ready callback
curdoc().on_event(DocumentReady, on_document_ready)

fake_slider = DateRangeSlider(title="Fake Range: ", start=date_i, end=date_f, value=( date_i, date_f ), step=1)
fake_slider.js_on_change('value', dimensions_callback)

# register callback to be called upon JS callback executions
window_size_data_source.on_change('data', on_dimensions_change)

# the layout name is added here then invoked from the HTML template
# all roots added here must be invoked on the HTML

layout1_h, layout2_h, layout3_h, layout1_v, layout2_v, layout3_v, controls1, controls2, plot1_map = make_layouts()

# by default layouts are created assuming we have enough width for the ideal visualization mode
# that is, we start with horizontal layouts

# section 1
curdoc().add_root(controls1)
curdoc().add_root(layout1_h)

# section 2
curdoc().add_root(controls2)
curdoc().add_root(layout2_h)

# section 3
curdoc().add_root(layout3_h)
