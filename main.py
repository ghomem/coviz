import numpy as np
import pandas as pd

from bokeh.io import curdoc
from bokeh.layouts import layout,gridplot, column, row
from bokeh.models import Button, Toggle, CategoricalColorMapper, ColumnDataSource, HoverTool, Label, SingleIntervalTicker, Slider, Spacer
from bokeh.palettes import Spectral6
from bokeh.plotting import figure

from .data import process_data

PAGE_TITLE = 'Coviz'

PLOT_TOOLS    ='save,reset,pan,wheel_zoom,box_zoom'

PLOT_HEIGHT   = 250
PLOT_WIDTH    = 400
TEXT_WIDTH    = 300
LMARGIN_WIDTH = 20

PLOT_LINE_WIDTH          = 3
PLOT_LINE_WIDTH_CRITICAL = 2

PLOT_LINE_ALPHA = 0.6

PLOT_X_LABEL  = 'Days'
PLOT_Y_LABEL  = 'Count'
PLOT_Y_LABEL2 = 'Value'

PLOT_LINE_COLOR           = 'gray'
PLOT_LINE_COLOR_HIGHLIGHT = 'orange'
PLOT_LINE_COLOR_REFERENCE = 'black'
PLOT_LINE_COLOR_CRITICAL  = 'red'

PLOT1_TITLE  ='14 Day incidence'
PLOT2_TITLE  ='PCR Positivity'
PLOT3_TITLE  ='Hospitalized'
PLOT4_TITLE  ='Case fatality rate'
PLOT5_TITLE  ='New cases'
PLOT6_TITLE  ='Covid deaths'
PLOT7_TITLE  ='Mortality'
PLOT8_TITLE  ='Rt'
PLOT9_TITLE  ='New cases by age group'
PLOT10_TITLE ='Risk diagram'

CLINES_LABEL = 'Show limits'
CLINES_SWITCH_WIDTH = 140
CLINES_SWITCH_HEIGHT = 30

# epidemic management red lines

INCIDENCE_LIMIT  = 120
POSITIVITY_LIMIT = 4
UCI_LIMIT        = 245
RT_LIMIT         = 1

def make_plot( name, title, range ):
    return figure(plot_height=PLOT_HEIGHT, plot_width=PLOT_WIDTH, title=title, tools=PLOT_TOOLS, x_range=[0, range], name=name, )

# set properties common to all the plots
def set_plot_details ( aplot, xlabel = PLOT_X_LABEL, ylabel = PLOT_Y_LABEL, xtooltip_format = "@x{0}", ytooltip_format = "@y{0}", tooltip_mode ='mouse', show_y_label = False ):
    aplot.toolbar.active_drag    = None
    aplot.toolbar.active_scroll  = None
    aplot.toolbar.active_tap     = None

    # add the hover tool
    ahover = HoverTool(tooltips=[ (xlabel, xtooltip_format), (ylabel, ytooltip_format)], mode=tooltip_mode)
    ahover.point_policy='snap_to_data'
    ahover.line_policy='nearest'
    aplot.add_tools(ahover)
    aplot.toolbar.active_inspect = ahover

    # control placement / visibility of toolbar
    aplot.toolbar_location       = None

    # labels
    aplot.xaxis.axis_label = xlabel
    if show_y_label:
        aplot.yaxis.axis_label = ylabel

# for the toggle button action
def update_state(new):

    cline1.visible = clines_switch.active
    cline2.visible = clines_switch.active
    cline3.visible = clines_switch.active
    cline4.visible = clines_switch.active


# main

curdoc().title = PAGE_TITLE

data_dates, data_new, data_hosp, data_hosp_uci, data_cv19_deaths, data_incidence, data_cfr, data_rt, data_pcr_pos, data_total_deaths, data_avg_deaths = process_data()

days=len(data_new)

# common x axis
x = np.linspace(1, days, days)

# one

source_plot1 = ColumnDataSource(data=dict(x=x, y=data_incidence))
plot1 = make_plot ('incidence', PLOT1_TITLE, days)
plot1.line('x', 'y', source=source_plot1, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )
set_plot_details(plot1)

# two

source_plot2 = ColumnDataSource(data=dict(x=x, y=data_pcr_pos))
plot2 = make_plot ('pcr_pos', PLOT2_TITLE, days)
plot2.line('x', 'y', source=source_plot2, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )
set_plot_details(plot2, 'Days', '%', "@x{0}", "@y{0.00}")

# three

plot3 = make_plot ('hosp', PLOT3_TITLE, days)
source1_plot3 = ColumnDataSource(data=dict(x=x, y=data_hosp))
source2_plot3 = ColumnDataSource(data=dict(x=x, y=data_hosp_uci))
plot3.line('x', 'y', source=source1_plot3, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, legend_label='Total' )
plot3.line('x', 'y', source=source2_plot3, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR_HIGHLIGHT, legend_label='UCI' )
plot3.legend.location = 'top_left'
set_plot_details(plot3, 'Days', 'Count', "@x{0}", "@y{0}", "mouse")

plot3.legend.label_text_font_size = "12px"

# four

source_plot4 = ColumnDataSource(data=dict(x=x, y=data_cfr))
plot4 = make_plot ('cfr', PLOT4_TITLE, days)
plot4.line('x', 'y', source=source_plot4, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )
set_plot_details(plot4, 'Days', '%', "@x{0}", "@y{0.00}",)

# five

source_plot5 = ColumnDataSource(data=dict(x=x, y=data_new))
plot5 = make_plot ('new', PLOT5_TITLE, days)
plot5.line('x', 'y', source=source_plot5, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )
set_plot_details(plot5)

# six

source_plot6 = ColumnDataSource(data=dict(x=x, y=data_rt))
plot6 = make_plot ('rt', PLOT8_TITLE, days)
plot6.line('x', 'y', source=source_plot6, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR,  )
set_plot_details(plot6, 'Days', 'Value',  "@x{0}", "@y{0.00}")

# seven

source1_plot7 = ColumnDataSource(data=dict(x=x, y=data_total_deaths))
source2_plot7 = ColumnDataSource(data=dict(x=x, y=data_avg_deaths))
source3_plot7 = ColumnDataSource(data=dict(x=x, y=data_cv19_deaths))
plot7 = make_plot ('total deaths', PLOT7_TITLE, days)
plot7.line('x', 'y', source=source1_plot7, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, legend_label='Total' )
plot7.line('x', 'y', source=source2_plot7, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR_REFERENCE, legend_label='2015-2019' )
#plot7.line('x', 'y', source=source3_plot7, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR_HIGHLIGHT, legend_label='Covid19')
plot7.legend.location = 'top_left'
set_plot_details(plot7, 'Days', 'Count', "@x{0}", "@y{0}", "mouse")

plot7.legend.label_text_font_size = "12px"

# eight

source_plot8 = ColumnDataSource(data=dict(x=x, y=data_cv19_deaths))
plot8 = make_plot ('deaths', PLOT6_TITLE, days)
plot8.line('x', 'y', source=source_plot8, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR,  )
set_plot_details(plot8)

# Critical lines
# default, primary, success, warning, danger, light
clines_switch = Toggle(label=CLINES_LABEL, button_type='default', align='end', width=CLINES_SWITCH_WIDTH, height=CLINES_SWITCH_HEIGHT, name = 'section1_button')
clines_switch.on_click(update_state)

source_plot1_critical = ColumnDataSource(data=dict(x=x, y=np.full( days, INCIDENCE_LIMIT )))
source_plot2_critical = ColumnDataSource(data=dict(x=x, y=np.full( days, POSITIVITY_LIMIT )))
source_plot3_critical = ColumnDataSource(data=dict(x=x, y=np.full( days, UCI_LIMIT )))
source_plot6_critical = ColumnDataSource(data=dict(x=x, y=np.full( days, RT_LIMIT )))

# critical lines
cline1 = plot1.line('x', 'y', source=source_plot3_critical, line_width=PLOT_LINE_WIDTH_CRITICAL, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR_CRITICAL)
cline2 = plot2.line('x', 'y', source=source_plot2_critical, line_width=PLOT_LINE_WIDTH_CRITICAL, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR_CRITICAL)
cline3 = plot3.line('x', 'y', source=source_plot3_critical, line_width=PLOT_LINE_WIDTH_CRITICAL, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR_CRITICAL)
cline4 = plot6.line('x', 'y', source=source_plot6_critical, line_width=PLOT_LINE_WIDTH_CRITICAL, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR_CRITICAL)

cline1.visible = False
cline2.visible = False
cline3.visible = False
cline4.visible = False

############## TBD #################

# FIXME get rid of this once we have the complete data
dummy=2
source_plot = ColumnDataSource(data=dict(x=x, y=np.full(days, dummy)))

plot9 = make_plot ('plot9', PLOT9_TITLE, days)
set_plot_details(plot9)

plot9.line('x', 'y', source=source_plot, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )

plot10 = make_plot ('plot10', PLOT10_TITLE, days)
set_plot_details(plot10)

plot10.line('x', 'y', source=source_plot, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )

############## TBD #################

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

layout2 = layout([ [plot9, plot10],
                   ], 
                   sizing_mode='scale_width', name='section2')

curdoc().add_root(layout2)
