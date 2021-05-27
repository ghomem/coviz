import math
import numpy as np
import pandas as pd

from bokeh.io import curdoc
from bokeh.layouts import layout,gridplot, column, row
from bokeh.models import Button, Toggle, CategoricalColorMapper, ColumnDataSource, HoverTool, Label, SingleIntervalTicker, Slider, Spacer, GlyphRenderer
from bokeh.palettes import Inferno256, Magma256, Turbo256, Plasma256, Cividis256, Viridis256
from bokeh.plotting import figure

from .data import process_data

PAGE_TITLE = 'Coviz'

PLOT_TOOLS    ='save,reset,pan,wheel_zoom,box_zoom'

PLOT_HEIGHT   = 250 # first section, but the actual height is constrained by the width
PLOT_WIDTH    = 400
PLOT_HEIGHT2  = 160 # for the second section
TEXT_WIDTH    = 300
LMARGIN_WIDTH = 20

PLOT_LINE_WIDTH          = 3
PLOT_LINE_WIDTH_CRITICAL = 2

PLOT_LINE_ALPHA       = 0.6
PLOT_LINE_ALPHA_MUTED = 0.1

PLOT_X_LABEL  = 'Days'
PLOT_Y_LABEL  = 'Count'
PLOT_Y_LABEL2 = 'Value'

PLOT_LINE_COLOR           = 'gray'
PLOT_LINE_COLOR_HIGHLIGHT = 'orange'
PLOT_LINE_COLOR_REFERENCE = 'black'
PLOT_LINE_COLOR_CRITICAL  = 'red'

PLOT_LINE_COLOR_PALETTE = Plasma256

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

def make_age_labels ( nr_labels ):

    labels = []
    for j in range(0, nr_labels):
        if j == len(data_strat_new) - 1:
            labels.append('>= ' + str(j*10))
        else:
            labels.append(str(j*10) + '-' + str((j+1)*10-1))

    return labels

def make_plot( name, title, range ):
    return figure(plot_height=PLOT_HEIGHT, plot_width=PLOT_WIDTH, title=title, tools=PLOT_TOOLS, x_range=[0, range], name=name, )

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

# set properties common to all the plots
def set_plot_details ( aplot, xlabel = PLOT_X_LABEL, ylabel = PLOT_Y_LABEL, xtooltip_format = "@x{0}", ytooltip_format = "@y{0}", tooltip_mode ='vline', show_x_label = True, show_y_label = False, ylabel2 = PLOT_Y_LABEL, ytooltip_format2 = None, tooltip_line = None ):
    aplot.toolbar.active_drag    = None
    aplot.toolbar.active_scroll  = None
    aplot.toolbar.active_tap     = None

    # add the hover tool
    tooltip_attachment = 'vertical'
    tooltip_list = [ (ylabel, ytooltip_format), (xlabel, xtooltip_format) ]

    # check if we have a second line for tooltips
    if ytooltip_format2:
        tooltip_list.insert( 1, (ylabel2, ytooltip_format2) )

    # we pass a single render to anchor the tooltip to a specific line
    if tooltip_line:
        ahover = HoverTool(tooltips=tooltip_list, mode=tooltip_mode, attachment=tooltip_attachment, renderers = [ tooltip_line ])
    else:
        rlist  = aplot.select(dict(type=GlyphRenderer))
        if len(rlist) > 0:
            ahover = HoverTool(tooltips=tooltip_list, mode=tooltip_mode, attachment=tooltip_attachment, renderers = [ rlist[0] ])
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

def set_plot_details_multi ( aplot, xlabel = PLOT_X_LABEL, ylabels = [], xtooltip_format = "@x{0}", tooltip_mode ='vline', tooltip_line = None, extra_precision = False ):
    aplot.toolbar.active_drag    = None
    aplot.toolbar.active_scroll  = None
    aplot.toolbar.active_tap     = None

    # add the hover tool
    tooltip_attachment = 'horizontal'
    tooltip_list = [ (xlabel, xtooltip_format) ]

    nr_series = len(ylabels)
    j = 0
    for label in ylabels:
        if extra_precision:
            ytooltip_format = "@y"+str(j)+"{0.00}"
        else:
            ytooltip_format = "@y"+str(j)+"{0}"
        j = j + 1
        tooltip_list.insert( 1, (label, ytooltip_format ))

    # we pass a single render to anchor the tooltip to a specific line
    if tooltip_line:
        ahover = HoverTool(tooltips=tooltip_list, mode=tooltip_mode, attachment=tooltip_attachment, renderers = [ tooltip_line ])
    else:
        rlist  = aplot.select(dict(type=GlyphRenderer))
        if len(rlist) > 0:
            print('aaaaa')
            ahover = HoverTool(tooltips=tooltip_list, mode=tooltip_mode, attachment=tooltip_attachment, renderers = [ rlist[0] ])
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

    aplot.legend.location = 'top_left'
    aplot.legend.click_policy = 'mute'

# for the toggle button action
def update_state(new):

    cline1.visible = clines_switch.active
    cline2.visible = clines_switch.active
    cline3.visible = clines_switch.active
    cline4.visible = clines_switch.active


# main

curdoc().title = PAGE_TITLE

data_dates, data_new, data_hosp, data_hosp_uci, data_cv19_deaths, data_incidence, data_cfr, data_rt, data_pcr_pos, data_total_deaths, data_avg_deaths, data_strat_new, data_strat_cv19_deaths, data_strat_cfr, data_vacc_1d, data_vacc_2d = process_data()

days=len(data_new)

# common x axis
x = np.linspace(1, days, days)

# one

source_plot1 = make_data_source(x, data_incidence)
plot1 = make_plot ('incidence', PLOT1_TITLE, days)
l11 = plot1.line('x', 'y', source=source_plot1, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )
set_plot_details(plot1)

# two

source_plot2 = make_data_source(x, data_pcr_pos)
plot2 = make_plot ('pcr_pos', PLOT2_TITLE, days)
plot2.line('x', 'y', source=source_plot2, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )
set_plot_details(plot2, 'Days', '%', "@x{0}", "@y{0.00}")

# three

plot3 = make_plot ('hosp', PLOT3_TITLE, days)
source_plot3 = make_data_source2(x, data_hosp, data_hosp_uci)
l31 = plot3.line('x', 'y',  source=source_plot3, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, legend_label='Total' )
l32 = plot3.line('x', 'y2', source=source_plot3, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR_HIGHLIGHT, legend_label='UCI' )

plot3.legend.location = 'top_left'
set_plot_details(plot3, 'Days', 'Total', "@x{0}", "@y{0}", "vline", True, False,'UCI', "@y2{0}", l31)

plot3.legend.label_text_font_size = "12px"

# four

source_plot4 = make_data_source(x, data_cfr)
plot4 = make_plot ('cfr', PLOT4_TITLE, days)
plot4.line('x', 'y', source=source_plot4, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )
set_plot_details(plot4, 'Days', '%', "@x{0}", "@y{0.00}",)

# five

source_plot5 = make_data_source(x, data_new)
plot5 = make_plot ('new', PLOT5_TITLE, days)
plot5.line('x', 'y', source=source_plot5, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )
set_plot_details(plot5)

# six

source_plot6 = make_data_source(x, data_rt)
plot6 = make_plot ('rt', PLOT8_TITLE, days)
plot6.line('x', 'y', source=source_plot6, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR,  )
set_plot_details(plot6, 'Days', 'Value',  "@x{0}", "@y{0.00}")

# seven

source_plot7 = make_data_source2(x, data_total_deaths, data_avg_deaths)
plot7 = make_plot ('total deaths', PLOT7_TITLE, days)
l71 = plot7.line('x', 'y',  source=source_plot7, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, legend_label='Current' )
l72 = plot7.line('x', 'y2', source=source_plot7, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR_REFERENCE, legend_label='2015-2019' )
plot7.legend.location = 'top_left'
set_plot_details(plot7, 'Days', 'Current', "@x{0}", "@y{0}", "vline", True, False,'2015-2019', "@y2{0}", l71)

plot7.legend.label_text_font_size = "12px"

# eight

source_plot8 = make_data_source(x, data_cv19_deaths)
plot8 = make_plot ('deaths', PLOT6_TITLE, days)
plot8.line('x', 'y', source=source_plot8, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR,  )
set_plot_details(plot8)

# Critical lines
# default, primary, success, warning, danger, light
clines_switch = Toggle(label=CLINES_LABEL, button_type='default', align='end', width=CLINES_SWITCH_WIDTH, height=CLINES_SWITCH_HEIGHT, name = 'section1_button')
clines_switch.on_click(update_state)

source_plot1_critical = make_data_source(x, np.full( days, INCIDENCE_LIMIT ))
source_plot2_critical = make_data_source(x, np.full( days, POSITIVITY_LIMIT ))
source_plot3_critical = make_data_source(x, np.full( days, UCI_LIMIT ))
source_plot6_critical = make_data_source(x, np.full( days, RT_LIMIT ))

# critical lines
cline1 = plot1.line('x', 'y', source=source_plot3_critical, line_width=PLOT_LINE_WIDTH_CRITICAL, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR_CRITICAL)
cline2 = plot2.line('x', 'y', source=source_plot2_critical, line_width=PLOT_LINE_WIDTH_CRITICAL, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR_CRITICAL)
cline3 = plot3.line('x', 'y', source=source_plot3_critical, line_width=PLOT_LINE_WIDTH_CRITICAL, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR_CRITICAL)
cline4 = plot6.line('x', 'y', source=source_plot6_critical, line_width=PLOT_LINE_WIDTH_CRITICAL, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR_CRITICAL)

cline1.visible = False
cline2.visible = False
cline3.visible = False
cline4.visible = False

# second page

nr_series = len(data_strat_new)
labels = make_age_labels(nr_series)
palette = PLOT_LINE_COLOR_PALETTE

# spacing the color as much as possible
color_multiplier = math.floor(256 / nr_series + 1)

# nine

source_plot9 = make_data_source_multi (x, data_strat_new)
plot9 = make_plot ('plot9', PLOT9_TITLE, days)

lines = []
for j in range(0, nr_series ):
    lines.append( plot9.line('x', 'y'+str(j), source=source_plot9, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=palette[color_multiplier * j], muted_alpha=PLOT_LINE_ALPHA_MUTED, legend_label=labels[j] ) )

# we know by inspection that line representing 40-49 is on top
set_plot_details_multi(plot9, 'Days', labels, "@x{0}", "vline", lines[4])

# ten

source_plot10 = make_data_source_multi (x, data_strat_cv19_deaths)
plot10 = make_plot ('plot10', PLOT10_TITLE, days)

lines = []
for j in range(0, nr_series ):
    lines.append( plot10.line('x', 'y'+str(j), source=source_plot10, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=palette[color_multiplier * j], muted_alpha=PLOT_LINE_ALPHA_MUTED, legend_label=labels[j] ) )

# the line for >= 80 is on top for this case
set_plot_details_multi(plot10, 'Days', labels, "@x{0}", "vline", lines[nr_series -1 ])

# eleven

source_plot11 = make_data_source_multi (x, data_strat_cfr)
plot11 = make_plot ('plot11', PLOT11_TITLE, days)

lines = []
for j in range(0, nr_series ):
    lines.append( plot11.line('x', 'y'+str(j), source=source_plot11, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=palette[color_multiplier * j], muted_alpha=PLOT_LINE_ALPHA_MUTED, legend_label=labels[j] ) )

# the line for >= 80 is on top for this case
set_plot_details_multi(plot11, 'Days', labels, "@x{0}", "vline", lines[nr_series -1 ], True)

# twelve

source_plot12 = make_data_source2(x, data_vacc_1d, data_vacc_2d)
plot12 = make_plot ('vaccination', PLOT12_TITLE, days)
l121 = plot12.line('x', 'y',  source=source_plot12, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, legend_label='Partial' )
l122 = plot12.line('x', 'y2', source=source_plot12, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR_HIGHLIGHT, legend_label='Complete' )
plot12.legend.location = 'top_left'
set_plot_details(plot12, 'Days', 'Partial', "@x{0}", "@y{0}", "vline", False, False,'Complete', "@y2{0}", l121)

plot12.legend.label_text_font_size = "12px"

#### Plot layout section ###

# the layout name is added here then invoked from the HTML template
# all roots added here must be invoked on the GRML

# section 1

curdoc().add_root(clines_switch)

grid = gridplot([ 
                  [ plot1, plot3, plot5, plot7 ],
                  [ plot2, plot4, plot6, plot8 ] ],
                  plot_width=PLOT_WIDTH, plot_height=PLOT_HEIGHT, toolbar_location=None, sizing_mode='scale_width')

layout1 = layout( grid, name='section1', sizing_mode='scale_width')

curdoc().add_root(layout1)

# section 2

grid2 = gridplot ([
                   [plot9,  plot11],
                   [plot10, plot12] ], 
                   plot_width=PLOT_WIDTH, plot_height=PLOT_HEIGHT2, toolbar_location=None, sizing_mode='scale_width')

layout2 = layout( grid2, name='section2', sizing_mode='scale_width')

curdoc().add_root(layout2)
