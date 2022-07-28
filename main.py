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
from bokeh.models.widgets import Tabs, Panel
from bokeh.models import Button, Toggle, CategoricalColorMapper, ColumnDataSource, TableColumn, DataTable, HoverTool, Label, SingleIntervalTicker, Slider, Spacer, GlyphRenderer, DatetimeTickFormatter, DateRangeSlider, DataRange1d, Range1d, DateSlider, LinearColorMapper, Div, CustomJS, Band, HTMLTemplateFormatter, StringFormatter, BoxAnnotation, Scatter
from bokeh.palettes import Inferno256, Magma256, Turbo256, Plasma256, Cividis256, Viridis256, OrRd
from bokeh.plotting import figure
from bokeh.events import DocumentReady

from .data import get_data, get_data_counties

# import configuration variables
from config import *

# import functions
from util import *

window_size_data_source = ColumnDataSource( data = { 'width' :[0] ,  'height': [0] } )

# by default we assume the layout is horizontal
current_horizontal = True

# functions

# note: callbacks and layout related functions act on global variables

### callbacks ####

# for the toggle button action
def update_state(new):

    cline1.visible = clines_switch.active
    cline2.visible = clines_switch.active
    cline3.visible = clines_switch.active
    cline4.visible = clines_switch.active

# for the visible stats
def update_stats(attr, old, new):

    date_i_cmp = date_slider1.value_as_date[0]
    date_f_cmp = date_slider1.value_as_date[1]

    # we need to know the list positions to sum the numbers
    idx1 = (date_i_cmp-data_dates[0]).days
    idx2 = (date_f_cmp-data_dates[0]).days

    # use nansum because there may be NaNs due to delayed / missing data

    sum_new              = make_html_integer(np.nansum(np.array( raw_data_new         [idx1:idx2+1] )))
    sum_cv19_deaths      = make_html_integer(np.nansum(np.array( raw_data_cv19_deaths [idx1:idx2+1] )))
    sum_total_deaths_pre = np.nansum(np.array( raw_data_total_deaths[idx1:idx2+1] ))

    sum_avg_deaths_pre   = int(round( np.nansum(np.array( raw_data_avg_deaths[idx1:idx2+1] ) ), 0))

    excess_deaths     = sum_total_deaths_pre - sum_avg_deaths_pre
    excess_deaths_pct = round( (excess_deaths / sum_avg_deaths_pre)*100, 1)

    sum_avg_deaths   = make_html_integer( sum_avg_deaths_pre   )
    sum_total_deaths = make_html_integer( sum_total_deaths_pre )

    # this is what is necessary to update an existing table

    # local vars
    stats_data = pd.DataFrame( { 'updated': str(data_dates[-1]), 'sum_new': [sum_new], 'sum_cv19_deaths': [sum_cv19_deaths], 'sum_total_deaths': [sum_total_deaths], 'sum_avg_deaths': [sum_avg_deaths], 'excess_deaths': [excess_deaths], 'excess_deaths_pct': [excess_deaths_pct] } )
    stats_source = ColumnDataSource( stats_data )

    # pre-existing global var
    stats_table.source = stats_source

# makes the legends appear / disappear as necessary
def update_legends(attr, old, new):

    date_i_cmp = date_slider1.value_as_date[0]
    date_f_cmp = date_slider1.value_as_date[1]

    # we need to know the list positions to sum the numbers
    idx1 = (date_i_cmp-data_dates[0]).days
    idx2 = (date_f_cmp-data_dates[0]).days

    # the -7 is because we start 7 days later on the dates, due to the moving average :-)
    if idx2-idx1 < days - 7:
        my_visibility = False
    else:
        my_visibility = True

    # plots that have dynamic legend
    plot3.legend.visible = my_visibility
    plot7.legend.visible = my_visibility

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

    new_data_incidence_counties, xxx, yyy = get_data_counties( date )

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

# for the overall mortality plot
def update_mortality_plot_range (attr, old, new):

    pre_box.right = date_slider4.value[0]
    post_box.left = date_slider4.value[1]

def update_mortality_stats (attr, old, new):

    date_i_cmp = date_slider4.value_as_date[0]
    date_f_cmp = date_slider4.value_as_date[1]

     # we need to know the list positions to sum the numbers
    idx1 = (date_i_cmp-data_dates[0]).days
    idx2 = (date_f_cmp-data_dates[0]).days

    column_total = []
    column_avg   = []
    column_exc   = []
    column_pct   = []

    # we use the non smoothed version for the stats
    for total_strat_group, avg_strat_group, avg_strat_group_inf, avg_strat_group_sup in zip(total_deaths_strat, avg_deaths_strat, avg_deaths_strat_inf, avg_deaths_strat_sup):

        # use nansum because there may be NaNs due to delayed / missing data

        sum_total_deaths = round(np.nansum(np.array( total_strat_group[idx1:idx2+1] )),0)
        column_total.append(sum_total_deaths)

        sum_avg_deaths     = round(np.nansum(np.array( avg_strat_group    [idx1:idx2+1] )),0)
        sum_avg_deaths_inf = round(np.nansum(np.array( avg_strat_group_inf[idx1:idx2+1] )),0)
        sum_avg_deaths_sup = round(np.nansum(np.array( avg_strat_group_sup[idx1:idx2+1] )),0)

        sum_avg_deaths_inf_pct = round(( ( sum_avg_deaths_inf - sum_avg_deaths ) / sum_avg_deaths ) * 100, 1)
        sum_avg_deaths_sup_pct = round(( ( sum_avg_deaths_sup - sum_avg_deaths ) / sum_avg_deaths ) * 100, 1)

        # the inf and sup values are symmetrical, so using only one of them simplifies the notation
        str_avg_deaths = '{:⁢<6} ± {}'.format(int(sum_avg_deaths), sum_avg_deaths_sup_pct)

        # we have to do some funky padding because the normal python format can not insert &nbsp;
        # and the HTML cells do away with normal spaces

        str_tmp = str(int(sum_avg_deaths))
        nspaces = 6 - len(str_tmp)

        str_spaces = '&nbsp;' * nspaces

        str_avg_deaths = str_tmp + str_spaces + ' ± ' + str(sum_avg_deaths_sup_pct) + '%'

        column_avg.append(str_avg_deaths)

        excess_deaths = sum_total_deaths - sum_avg_deaths

        # to compensate for the minus sign
        str_pad = ''
        if excess_deaths > 0:
            str_pad = '&nbsp;'

        column_exc.append( str_pad + str(int(excess_deaths)) )

        column_pct.append( str_pad + str(round( (excess_deaths / sum_avg_deaths)*100, 1)) + '%' )

    # this is what is necessary to update an existing table

    # local vars
    dummy_column = [ 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1 , 1]
    index_column = [ '<1', '1-4', '5-14', '15-24','25-34', '35-44', '45-54', '55-64', '65-74', '75-84', '>85', 'all ages', 'all ages*' ]

    stats_data = pd.DataFrame( { 'age_group': index_column, 'sum_total_deaths': column_total, 'sum_avg_deaths': column_avg, 'excess_deaths': column_exc, 'excess_deaths_pct': column_pct } )
    stats_source = ColumnDataSource( stats_data )

    # pre-existing global var
    mortality_stats_table.source = stats_source

    # update table caption
    mortality_notes.text = 'Data for period of ' + str(date_i_cmp) + ' to ' + str(date_f_cmp)

    # and for the correlation plot

    data_cv19_deaths_subset = get_clean_data(corr_data_cv19_deaths[idx1:idx2+1])
    data_exc_deaths_subset  = get_clean_data(corr_data_exc_deaths [idx1:idx2+1])

    slope, intercept, r_value = get_correlation_data (data_cv19_deaths_subset, data_exc_deaths_subset)

    # update the global variables
    source_plot_correlation.data = dict(x=data_cv19_deaths_subset, y=data_exc_deaths_subset)
    correlation_coefficient      = r_value

    regression_line.gradient    = slope
    regression_line.y_intercept = intercept

    label_str = make_correlation_str(slope, intercept, r_value)
    regression_label.text       = label_str


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
            curdoc().add_root(layout4_h)
            curdoc().add_root(layout5_h)
            curdoc().add_root(layout6_h)
            curdoc().add_root(layout7)
        else:
            curdoc().add_root(layout2_v)
            curdoc().add_root(layout3_v)
            curdoc().add_root(layout4_v)
            curdoc().add_root(layout5_v)
            curdoc().add_root(layout6_v)
            curdoc().add_root(layout7)

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

#### end of callbacks ####

### layouts ####

def make_layouts( ):

    control_spacer = Spacer(width=10, height=10, width_policy='auto', height_policy='fixed')

    # use this line for debugging with the fake slider
    controls1 = row (date_slider1, control_spacer, fake_slider, clines_switch, name="section1_controls" )

    fake_slider.visible = False

    # first

    grid_h = gridplot([
                      [ plot1, plot3, plot5, plot8 ],
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
    set_plot_date_details(plot1_copy, data_dates, days, source_plot1)

    # but we change the range
    # we can't do this on a directy copy of plot1, because it is shallow
    plot1_copy.x_range.start = pd.to_datetime(map_date_i)
    plot1_copy.x_range.end   = pd.to_datetime(map_date_f)

    notes = Div(text=TEXT_NOTES, width=TEXT_WIDTH)

    # now the layout

    slider_spacer = Spacer(width=30, height=50, width_policy='auto', height_policy='fixed')

    layout1_h = layout( column(stats_table,grid_h), name='section1', sizing_mode='scale_width')
    layout2_h = layout(grid2_h, name='section2', sizing_mode='scale_width')

    column_section3_map    = column(plot_map)
    column_section3_others = column( [plot1_copy, row( [slider_spacer, date_slider_map] ), row( [ slider_spacer, notes] ) ] )

    row_section3 = row ( column_section3_map , column_section3_others )
    layout3_h = layout( row_section3, name='section3')

    layout1_v = layout(column(stats_table,grid_v),  name='section1', sizing_mode='scale_width')
    layout2_v = layout(grid2_v, name='section2', sizing_mode='scale_width')

    # we don't need the notes text on the vertical layout
    column_section3_map = column( [plot_map, row( [slider_spacer, date_slider_map] ), plot1_copy ] )

    layout3_v = layout( column_section3_map, name='section3')

    # fourth

    # adds left side spacing for handles lining up with the annotation box
    slider_spacer4 = Spacer(width=40, height=100, width_policy='auto', height_policy='fixed')

    mortality_plots_column = column(mort_explorer_tabset, row(slider_spacer4, date_slider4))

    in_between_spacer   = Spacer(width=20, height=50, width_policy='auto', height_policy='fixed')
    in_between_spacer_v = Spacer(width=20, height=10, width_policy='auto', height_policy='fixed')

    # the mortality columns come from main
    layout4_h = layout(row   (mortality_plots_column, in_between_spacer, mort_explorer_tabset2), name='section4', sizing_mode='scale_width')
    layout4_v = layout(column(mortality_plots_column, mort_explorer_tabset2), name='section4', sizing_mode='scale_width')

    # fifth

    prev_spacer  = Spacer(width=20, height=5, width_policy='auto', height_policy='fixed')
    prev_spacer2 = Spacer(width=20, height=60, width_policy='auto', height_policy='fixed')
    layout5_h = layout(row (plot_prevalence, prev_spacer, column(prev_spacer,prevalence_notes, prev_spacer2) ), name='section5', sizing_mode='scale_width')

    layout5_v = layout(column (plot_prevalence), name='section5', sizing_mode='scale_width')

    # sixth

    vacc_risk_spacer   = Spacer(width=20, height=5, width_policy='auto', height_policy='fixed')
    vacc_risk_spacer2  = Spacer(width=20, height=5, width_policy='auto', height_policy='fixed')
    vacc_risk_spacer_v = Spacer(width=20, height=70, width_policy='auto', height_policy='fixed')

    layout6_h = layout(column(row (vacc_risk_cfr_tabset, vacc_risk_spacer, vacc_risk_chr_tabset, vacc_risk_spacer2, vacc_risk_notes), vacc_risk_spacer_v ), name='section6', sizing_mode='scale_width')

    layout6_v = layout(column(vacc_risk_cfr_tabset, vacc_risk_spacer, vacc_risk_chr_tabset), name='section6', sizing_mode='scale_width')

    # seventh

    layout7 = layout(column(final_notes), name='section7', sizing_mode='scale_width')

    return layout1_h, layout2_h, layout3_h, layout1_v, layout2_v, layout3_v, controls1, controls2, plot1_copy,\
    layout4_h, layout4_v, layout5_h, layout5_v, layout6_h, layout6_v, layout7

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


### end of layouts ####

### main ###

curdoc().title = PAGE_TITLE

# fetch data from files

# data for regular plots
data_dates, data_dates2, processed_data, raw_data = get_data()

data_new               = processed_data[0]
data_hosp              = processed_data[1]
data_hosp_uci          = processed_data[2]
data_cv19_deaths       = processed_data[3]
data_incidence         = processed_data[4]
data_cfr               = processed_data[5]
data_rt                = processed_data[6]
data_pos               = processed_data[7]
data_total_deaths      = processed_data[8]
data_avg_deaths        = processed_data[9]
data_avg_deaths_inf    = processed_data[10]
data_avg_deaths_sup    = processed_data[11]
data_strat_new         = processed_data[12]
data_strat_cv19_deaths = processed_data[13]
data_strat_cfr         = processed_data[14]
data_vacc_part         = processed_data[15]
data_vacc_full         = processed_data[16]
data_vacc_boost        = processed_data[17]
data_strat_mort        = processed_data[18]
data_min_prevalence    = processed_data[19]
data_max_prevalence    = processed_data[20]
data_avg_prevalence    = processed_data[21]
data_vacc_cfr          = processed_data[22]
data_vacc_chr          = processed_data[23]

raw_data_new          = raw_data[0]
raw_data_cv19_deaths  = raw_data[1]
raw_data_total_deaths = raw_data[2]
raw_data_avg_deaths   = raw_data[3]

data_exc_deaths       = np.array(data_total_deaths) - np.array(data_avg_deaths)
raw_data_exc_deaths   = np.array(raw_data_total_deaths) - np.array(raw_data_avg_deaths)

# IMPORTANT
#
# We use the raw data for the excess mortality calculations
# but we are using the smoothed data for the correlation between
# excess mortality and cv mortality because doing otherwise leads
# to strange results such as week correlation between 26-09-2020 and 22-12-2020
# where the correlation is more than obvious (return to school, pre vax)
#
# It might be that the CV19 reporting dates might not match the dates reported
# by the eVM database, for the deaths events of the same people

corr_data_exc_deaths  = data_exc_deaths
corr_data_cv19_deaths = data_cv19_deaths

# map data
data_incidence_counties, map_date_i, map_date_f  = get_data_counties()

# our original data has one line per county, and each line contains a set of polygons
# for a performant map update on update_map we need to keep a converted version
# this version has multiple lines with the same index for counties that hove multipolygons
aux_df = convert_geoDataFrame_to_patches(data_incidence_counties, 'geometry')

# the conversion transforms lines that have multiple polygons into multiple lines with the same index
# index has repeated values because of that
aux_index = aux_df.index

# calculate the nr of days using the most reliable source

days = len(data_new)
days2 = len(data_dates2)

plot_data_s1 = []
plot_data_s2 = []

#### First page ####

# one

source_plot1 = make_data_source_dates(data_dates, data_incidence)
plot1 = make_plot ('incidence', PLOT1_TITLE, days, 'datetime')
l11 = plot1.line('x','y', source=source_plot1, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )
set_plot_details(plot1, 'Date', 'Count', '@x{%F}', '@y{0.00}', 'vline', False, False)
set_plot_date_details(plot1, data_dates, days, source_plot1)

plot_data_s1.append( (plot1, source_plot1) )

# two

source_plot2 = make_data_source_dates(data_dates, data_pos)
plot2 = make_plot ('positivity', PLOT2_TITLE, days, 'datetime')
l21 = plot2.line('x', 'y', source=source_plot2, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )
set_plot_details(plot2, 'Date', '%', '@x{%F}', '@y{0.00}', 'vline', False, False)
set_plot_date_details(plot2, data_dates, days, source_plot2)

plot_data_s1.append( (plot2, source_plot2) )

# three

#source_plot3 = make_data_source_dates(data_dates, data_hosp, list(np.array(data_hosp_uci)*5))

source_plot3 = ColumnDataSource(pd.DataFrame(data={ 'x': data_dates, 'y': data_hosp, 'y2': list(np.array(data_hosp_uci)*5), 'y3': data_hosp_uci }, columns=['x', 'y', 'y2', 'y3']))

plot3 = make_plot ('hosp', PLOT3_TITLE, days, 'datetime')
l31 = plot3.line('x', 'y',  source=source_plot3, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, legend_label='Total' )
l32 = plot3.line('x', 'y2', source=source_plot3, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR_HIGHLIGHT, legend_label='UCI x5' )

plot3.legend.location = 'top_left'
set_plot_details(plot3, 'Date', 'Total', '@x{%F}', '@y{0}', 'vline', False, False,'UCI', "@y3{0}", l31)
set_plot_date_details(plot3, data_dates, days, source_plot3)

plot3.legend.label_text_font_size = PLOT_LEGEND_FONT_SIZE

plot_data_s1.append( (plot3, source_plot3) )

# four

source_plot4 = make_data_source_dates(data_dates, data_cfr)
plot4 = make_plot ('cfr', PLOT4_TITLE, days, 'datetime')
plot4.line('x', 'y', source=source_plot4, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )
set_plot_details(plot4, 'Date', '%', '@x{%F}', '@y{0.00}', 'vline', False, False)
set_plot_date_details(plot4, data_dates, days)

plot_data_s1.append( (plot4, source_plot4) )

# five

source_plot5 = make_data_source_dates(data_dates, data_new)
plot5 = make_plot ('new', PLOT5_TITLE, days, 'datetime')
plot5.line('x', 'y', source=source_plot5, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )
set_plot_details(plot5, 'Date', 'Count', '@x{%F}', '@y{0}', 'vline', False, False)
set_plot_date_details(plot5, data_dates, days, source_plot5)

plot_data_s1.append( (plot5, source_plot5) )

# six

source_plot6 = make_data_source_dates(data_dates, data_rt)
plot6 = make_plot ('rt', PLOT8_TITLE, days, 'datetime')
plot6.line('x', 'y', source=source_plot6, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR,  )
set_plot_details(plot6, 'Date', 'Value', '@x{%F}', '@y{0.00}', 'vline', False, False)
set_plot_date_details(plot6, data_dates, days, source_plot6)

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
set_plot_date_details(plot7, data_dates, days, source_plot7)

plot7.legend.label_text_font_size = PLOT_LEGEND_FONT_SIZE

plot_data_s1.append( (plot7, source_plot7) )

# eight

source_plot8 = make_data_source_dates(data_dates, data_cv19_deaths)
plot8 = make_plot ('deaths', PLOT6_TITLE, days, 'datetime')
plot8.line('x', 'y', source=source_plot8, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR,  )
set_plot_details(plot8, 'Date', 'Count', '@x{%F}', '@y{0}', 'vline', False, False)
set_plot_date_details(plot8, data_dates, days, source_plot8)

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

# we want the plots to change in real time but the stats only to be updated after the user stopped moving the mouse
date_slider1.on_change('value', partial(update_plot_range, section="1"))
date_slider1.on_change('value', partial(update_legends))
date_slider1.on_change('value_throttled', partial(update_stats))

# the statistical summary

stats_table = make_stats_table (STATS_WIDTH, STATS_HEIGHT, 'end')

# the parameters are dummy as we take the values directly from the slider
update_stats(0,0,0)

#### Second page ####

nr_series = len(data_strat_new)
labels = make_age_labels(nr_series, nr_series)
palette = PLOT_LINE_COLOR_PALETTE

# spacing the color as much as possible
color_multiplier = math.floor(256 / nr_series + 1)

# nine

source_plot9 = make_data_source_multi_dates (data_dates2, data_strat_new)
plot9 = make_plot ('plot9', PLOT9_TITLE, days2, 'datetime')

lines = []
for j in range(0, nr_series ):
    lines.append( plot9.line('x', 'y'+str(j), source=source_plot9, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=palette[color_multiplier * j], muted_alpha=PLOT_LINE_ALPHA_MUTED, legend_label=labels[j] ) )

# we know by inspection that line representing 40-49 is on top
set_plot_details_multi(plot9, 'Date', labels, '@x{%F}', 'vline', lines[4], False, False)
set_plot_date_details(plot9, data_dates2, days2, source_plot9)

plot_data_s2.append( (plot9, source_plot9) )

# ten

source_plot10 = make_data_source_multi_dates (data_dates2, data_strat_cv19_deaths)
plot10 = make_plot ('plot10', PLOT10_TITLE, days2, 'datetime')

lines = []
for j in range(0, nr_series ):
    lines.append( plot10.line('x', 'y'+str(j), source=source_plot10, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=palette[color_multiplier * j], muted_alpha=PLOT_LINE_ALPHA_MUTED, legend_label=labels[j] ) )

# the line for >= 80 is on top for this case
set_plot_details_multi(plot10, 'Date', labels, '@x{%F}', 'vline', lines[nr_series -1 ], False, False)
set_plot_date_details(plot10, data_dates2, days2, source_plot10)

plot_data_s2.append( (plot10, source_plot10) )

# eleven

source_plot11 = make_data_source_multi_dates (data_dates2, data_strat_cfr)
plot11 = make_plot ('plot11', PLOT11_TITLE, days2, 'datetime')

lines = []
for j in range(0, nr_series ):
    lines.append( plot11.line('x', 'y'+str(j), source=source_plot11, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=palette[color_multiplier * j], muted_alpha=PLOT_LINE_ALPHA_MUTED, legend_label=labels[j] ) )

# the line for >= 80 is on top for this case
set_plot_details_multi(plot11, 'Days', labels, '@x{%F}', 'vline', lines[nr_series -1 ], True, False)
set_plot_date_details(plot11, data_dates2, days2, source_plot11)

plot_data_s2.append( (plot11, source_plot11) )

# twelve

df12 = pd.DataFrame(data={ 'x': data_dates2, 'y': data_vacc_part, 'y2': data_vacc_full, 'y3': data_vacc_boost }, columns=['x', 'y', 'y2', 'y3'])
source_plot12 = ColumnDataSource(df12)

plot12 = make_plot ('vaccination', PLOT12_TITLE, days, 'datetime')
l121 = plot12.line('x', 'y',  source=source_plot12, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, legend_label='Partial' )
l122 = plot12.line('x', 'y2', source=source_plot12, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR_HIGHLIGHT, legend_label='Complete' )
l122 = plot12.line('x', 'y3', source=source_plot12, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR_REFERENCE, legend_label='Booster' )
plot12.legend.location = 'top_left'
set_plot_details(plot12, 'Date', 'Partial', '@x{%F}', '@y{0}', 'vline', False, False,'Complete', "@y2{0}", l121, False, 'Booster', "@y3{0}")

set_plot_date_details(plot12, data_dates2, days2, source_plot12)

plot_data_s2.append( (plot12, source_plot12) )

# date range widget

# we use the earlier end date for this
date2_f = data_dates2[-1]
#
date_slider2 = DateRangeSlider(title="Date Range: ", start=date_i, end=date2_f, value=( date_i, date2_f ), step=1)

date_slider2.on_change('value', partial(update_plot_range, section="2"))

#### Third page ####

# pandas option, necessary for bokeh plots from pandas
pd.set_option('plotting.backend', 'pandas_bokeh')

plot_map, plot_map_s1 = make_map_plot ( data_incidence_counties )

# the step parameter is in miliseconds
step_days = 7
date_slider_map = DateSlider(title='Selected date', start=map_date_i, end=map_date_f, value=map_date_f, step = step_days*1000*60*60*24, width_policy='fixed', width=PLOT_WIDTH-40 )

date_slider_map.on_change('value_throttled', partial(update_map))

#### Fourth page ####

# the first one is raw, the second is smoothed
total_deaths_strat     = data_strat_mort[0]
s_total_deaths_strat   = data_strat_mort[1]

# the rigorous versions are used for the calculations
avg_deaths_strat       = data_strat_mort[2]
avg_deaths_strat_inf   = data_strat_mort[3]
avg_deaths_strat_sup   = data_strat_mort[4]

# we obtain the smooth versions for the plot
s_avg_deaths_strat       = data_strat_mort[5]
s_avg_deaths_strat_inf   = data_strat_mort[6]
s_avg_deaths_strat_sup   = data_strat_mort[7]

# we are smoothing the average historic mortality on the plot, but not the yellow bands as it does not seem visually necessary
p4_plot1  = make_mortality_plot ( data_dates, s_total_deaths_strat[0],  s_avg_deaths_strat[0],  avg_deaths_strat_inf[0],  avg_deaths_strat_sup[0],  days, '<1'        )
p4_plot2  = make_mortality_plot ( data_dates, s_total_deaths_strat[1],  s_avg_deaths_strat[1],  avg_deaths_strat_inf[1],  avg_deaths_strat_sup[1],  days, '1-4'       )
p4_plot3  = make_mortality_plot ( data_dates, s_total_deaths_strat[2],  s_avg_deaths_strat[2],  avg_deaths_strat_inf[2],  avg_deaths_strat_sup[2],  days, '5-14'      )
p4_plot4  = make_mortality_plot ( data_dates, s_total_deaths_strat[3],  s_avg_deaths_strat[3],  avg_deaths_strat_inf[3],  avg_deaths_strat_sup[3],  days, '15-24'     )
p4_plot5  = make_mortality_plot ( data_dates, s_total_deaths_strat[4],  s_avg_deaths_strat[4],  avg_deaths_strat_inf[4],  avg_deaths_strat_sup[4],  days, '25-34'     )
p4_plot6  = make_mortality_plot ( data_dates, s_total_deaths_strat[5],  s_avg_deaths_strat[5],  avg_deaths_strat_inf[5],  avg_deaths_strat_sup[5],  days, '35-44'     )
p4_plot7  = make_mortality_plot ( data_dates, s_total_deaths_strat[6],  s_avg_deaths_strat[6],  avg_deaths_strat_inf[6],  avg_deaths_strat_sup[6],  days, '45-54'     )
p4_plot8  = make_mortality_plot ( data_dates, s_total_deaths_strat[7],  s_avg_deaths_strat[7],  avg_deaths_strat_inf[7],  avg_deaths_strat_sup[7],  days, '55-64'     )
p4_plot9  = make_mortality_plot ( data_dates, s_total_deaths_strat[8],  s_avg_deaths_strat[8],  avg_deaths_strat_inf[8],  avg_deaths_strat_sup[8],  days, '65-74'     )
p4_plot10 = make_mortality_plot ( data_dates, s_total_deaths_strat[9],  s_avg_deaths_strat[9],  avg_deaths_strat_inf[9],  avg_deaths_strat_sup[9],  days, '75-84'     )
p4_plot11 = make_mortality_plot ( data_dates, s_total_deaths_strat[10], s_avg_deaths_strat[10], avg_deaths_strat_inf[10], avg_deaths_strat_sup[10], days, '>85'       )
p4_plot12 = make_mortality_plot ( data_dates, s_total_deaths_strat[11], s_avg_deaths_strat[11], avg_deaths_strat_inf[11], avg_deaths_strat_sup[11], days, 'all ages'  )

# for this special tab the overal deaths are the same, but the references (avg, inf and sup) have been corrected
p4_plot13 = make_mortality_plot ( data_dates, s_total_deaths_strat[12], s_avg_deaths_strat[12], avg_deaths_strat_inf[12], avg_deaths_strat_sup[12], days, 'all ages *')

p4_plots = [ p4_plot1, p4_plot2, p4_plot3, p4_plot4, p4_plot5, p4_plot6, p4_plot7, p4_plot8, p4_plot9, p4_plot10, p4_plot11, p4_plot12, p4_plot13 ]

tab1  = Panel(child=p4_plot1, title='<1'         )
tab2  = Panel(child=p4_plot2, title='1-4'        )
tab3  = Panel(child=p4_plot3, title='5-14'       )
tab4  = Panel(child=p4_plot4, title='15-24'      )
tab5  = Panel(child=p4_plot5, title='25-34'      )
tab6  = Panel(child=p4_plot6, title='35-44'      )
tab7  = Panel(child=p4_plot7, title='45-54'      )
tab8  = Panel(child=p4_plot8, title='55-64'      )
tab9  = Panel(child=p4_plot9, title='65-74'      )
tab10 = Panel(child=p4_plot10,title='75-84'      )
tab11 = Panel(child=p4_plot11,title='>85'        )
tab12 = Panel(child=p4_plot12,title='all ages'   )
tab13 = Panel(child=p4_plot13,title='all ages *' )

mort_explorer_tabset = Tabs(tabs=[ tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12, tab13 ])

# make sure the tab for all ages is selected
mort_explorer_tabset.active = 12

date_slider4 = DateRangeSlider(title="Date Range: ", start=date_i, end=date_f, value=( date_i, date_f ), step=1, width=PLOT_WIDTH4-50)

date_slider4.on_change('value', partial(update_mortality_plot_range))
date_slider4.on_change('value_throttled', partial(update_mortality_stats))

# annotations to visually mask the non-affected date range
# in the initial moment they are invisible because the left and right parameters are the same
pre_box  = BoxAnnotation(left=date_i, right=date_i, fill_alpha=PLOT_AREAS_ALPHA4, fill_color=PLOT_AREAS_COLOR4)
post_box = BoxAnnotation(left=date_f, right=date_f, fill_alpha=PLOT_AREAS_ALPHA4, fill_color=PLOT_AREAS_COLOR4)

for p in p4_plots:
    p.add_layout(pre_box)
    p.add_layout(post_box)

# the statistics table
mortality_stats_table = make_mortality_stats_table (MORT_STATS_TABLE_WIDTH, MORT_STATS_TABLE_HEIGHT, 'end')

# and its caption
mortality_notes  = Div(text='dummy', width=MORT_TEXT_WIDTH, align='center')

# plus the note for the special row
mortality_notes2 = Div(text='</br>* contains a correction for population aging that converts deaths from 2015-2019 into equivalent current year deaths', align='start')

# forces vertical alignement on the table stats column
table_spacer4_top  = Spacer(width=40, height=10, width_policy='auto', height_policy='fixed')

mortality_stats_column = column(table_spacer4_top, mortality_stats_table, mortality_notes, mortality_notes2)

# now let's create the correlation plot

# fix the data in case it has leading NaNs due to moving averages
# we assume the leading NaNs are the same for x and y, when they exist

clean_data_cv19_deaths = get_clean_data(corr_data_cv19_deaths)
clean_data_exc_deaths  = get_clean_data(corr_data_exc_deaths)

# height and width are the same because we want it to be square for easier reading
corr_width = MORT_STATS_TABLE_WIDTH

plot_correlation, source_plot_correlation, correlation_coefficient, regression_line, regression_label = make_correlation_plot ( clean_data_cv19_deaths, clean_data_exc_deaths, 'Covid deaths', 'Excess deaths', corr_width, corr_width)

table_spacer4_top2   = Spacer(width=40, height=1, width_policy='auto', height_policy='fixed')
table_spacer4_bottom = Spacer(width=40, height=5, width_policy='auto', height_policy='fixed')
mortality_correlation_column = column(table_spacer4_top2, plot_correlation, table_spacer4_bottom, mortality_notes)

# and a tabset for the table + plot

tab2_1 = Panel(child=mortality_stats_column,       title='Stats'       )
tab2_2 = Panel(child=mortality_correlation_column, title='Correlation' )

mort_explorer_tabset2 = Tabs(tabs=[ tab2_1, tab2_2 ])

# with the table selected by default

mort_explorer_tabset2.active = 0

# the parameters are dummy as we take the values directly from the slider
update_mortality_stats(0,0,0)

#### Fifth page ####

source_plot_prevalence = ColumnDataSource(pd.DataFrame(data={ 'x': data_dates, 'y': data_max_prevalence, 'y2': data_avg_prevalence, 'y3': data_min_prevalence,  }, columns=['x', 'y', 'y2', 'y3' ]))

plot_prevalence = make_plot ('prevalance', PLOT_PREVALENCE_TITLE, days, 'datetime', PLOT_HEIGHT5, PLOT_WIDTH5)
l_prev1 = plot_prevalence.line('x', 'y', source=source_plot_prevalence, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR_REFERENCE, legend_label='Max prevalence' )
l_prev2 = plot_prevalence.line('x', 'y2',source=source_plot_prevalence, line_width=PLOT_LINE_WIDTH, line_alpha=0.9, line_color=PLOT_LINE_COLOR, legend_label='Avg prevalence' )
l_prev3 = plot_prevalence.line('x', 'y3',source=source_plot_prevalence, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, legend_label='Min prevalence' )

plot_prevalence.legend.location = 'top_left'
set_plot_details(plot_prevalence, 'Date', 'Max %', '@x{%F}', '@y{0.00}', 'vline', False, False,'Avg %', "@y2{0.00}", l_prev1, True, 'Min %', "@y3{0.00}")
set_plot_date_details(plot_prevalence, data_dates, days, source_plot_prevalence)

plot_prevalence.legend.label_text_font_size = PLOT_LEGEND_FONT_SIZE

prevalence_notes = Div(text=PREV_TEXT, width=PREV_TEXT_WIDTH, align='start')

#### Sixth page ####

# one plot with CFR and CHR per age group

p6_plot_cfr_50_59   = make_vacc_risk_plot(data_vacc_cfr, VACC_CFR_TITLE, '50_59')
p6_plot_cfr_60_69   = make_vacc_risk_plot(data_vacc_cfr, VACC_CFR_TITLE, '60_69')
p6_plot_cfr_70_79   = make_vacc_risk_plot(data_vacc_cfr, VACC_CFR_TITLE, '70_79')
p6_plot_cfr_80_plus = make_vacc_risk_plot(data_vacc_cfr, VACC_CFR_TITLE, '80mais')

tab6_cfr_1 = Panel(child=p6_plot_cfr_50_59,   title='50-59')
tab6_cfr_2 = Panel(child=p6_plot_cfr_60_69,   title='60-69')
tab6_cfr_3 = Panel(child=p6_plot_cfr_70_79,   title='70-79')
tab6_cfr_4 = Panel(child=p6_plot_cfr_80_plus, title='>80')

p6_plot_chr_50_59   = make_vacc_risk_plot(data_vacc_chr, VACC_CHR_TITLE, '50_59')
p6_plot_chr_60_69   = make_vacc_risk_plot(data_vacc_chr, VACC_CHR_TITLE, '60_69')
p6_plot_chr_70_79   = make_vacc_risk_plot(data_vacc_chr, VACC_CHR_TITLE, '70_79')
p6_plot_chr_80_plus = make_vacc_risk_plot(data_vacc_chr, VACC_CHR_TITLE, '80mais')

tab6_chr_1 = Panel(child=p6_plot_chr_50_59,   title='50-59')
tab6_chr_2 = Panel(child=p6_plot_chr_60_69,   title='60-69')
tab6_chr_3 = Panel(child=p6_plot_chr_70_79,   title='70-79')
tab6_chr_4 = Panel(child=p6_plot_chr_80_plus, title='>80')

vacc_risk_cfr_tabset = Tabs(tabs=[ tab6_cfr_1, tab6_cfr_2, tab6_cfr_3, tab6_cfr_4 ])
vacc_risk_chr_tabset = Tabs(tabs=[ tab6_chr_1, tab6_chr_2, tab6_chr_3, tab6_chr_4 ])

vacc_risk_cfr_tabset.active = 3
vacc_risk_chr_tabset.active = 3

vacc_risk_notes = Div(text=VACC_RISK_TEXT, width=VACC_RISK_TEXT_WIDTH, align='start')

#### Seventh page ####

final_notes = Div(text=FINAL_TEXT, width=FINAL_TEXT_WIDTH, align='start')

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

layout1_h, layout2_h, layout3_h, layout1_v, layout2_v, layout3_v, controls1, controls2, plot1_map, \
layout4_h, layout4_v, layout5_h, layout5_v, layout6_h, layout6_v, layout7 = make_layouts()

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

# section 4
curdoc().add_root(layout4_h)

# section 5
curdoc().add_root(layout5_h)

# section 6
curdoc().add_root(layout6_h)

# section 7
curdoc().add_root(layout7)
