import numpy as np

from bokeh.io import curdoc
from bokeh.layouts import layout
from bokeh.models import Button, CategoricalColorMapper, ColumnDataSource, HoverTool, Label, SingleIntervalTicker, Slider
from bokeh.palettes import Spectral6
from bokeh.plotting import figure

from .data import process_data

PAGE_TITLE = 'Coviz'

PLOT_TOOLS    ='save,reset,pan,wheel_zoom,box_zoom'

PLOT_HEIGHT   = 300
PLOT_WIDTH    = 500
TEXT_WIDTH    = 300
LMARGIN_WIDTH = 20

PLOT_LINE_WIDTH = 3
PLOT_LINE_ALPHA = 0.6

PLOT_X_LABEL  = 'Days'
PLOT_Y_LABEL  = 'Count'
PLOT_Y_LABEL2 = 'Value'

PLOT_LINE_COLOR  = 'gray'
PLOT_LINE_COLOR2 = 'orange'

PLOT1_TITLE  ='14 Day incidence'
PLOT2_TITLE  ='PCR Positivity'
PLOT3_TITLE  ='Hospitalized, UCI'
PLOT4_TITLE  ='Case fatality rate'
PLOT5_TITLE  ='New cases'
PLOT6_TITLE  ='Covid deaths'
PLOT7_TITLE  ='Mortality (Covid, 5y avg, total)'
PLOT8_TITLE  ='Rt'
PLOT9_TITLE  ='New cases by age group'
PLOT10_TITLE ='Risk diagram'

def make_plot( name, title, range ):
    return figure(plot_height=PLOT_HEIGHT, plot_width=PLOT_WIDTH, title=title, tools=PLOT_TOOLS, x_range=[0, range], name=name)

# set properties common to all the plots
def set_plot_details ( aplot, xlabel = PLOT_X_LABEL, ylabel = PLOT_Y_LABEL ):
    aplot.toolbar.active_drag    = None
    aplot.toolbar.active_scroll  = None
    aplot.toolbar.active_tap     = None

    # add the hover tool
    ahover = HoverTool(tooltips=[ (xlabel, "@x{0}"), (ylabel, "@y{0}")], mode="mouse" )
    ahover.point_policy='snap_to_data'
    ahover.line_policy='nearest'
    aplot.add_tools(ahover)
    aplot.toolbar.active_inspect = ahover

    # control placement / visibility of toolbar
    aplot.toolbar_location       = None

    # labels
    aplot.xaxis.axis_label = xlabel
    aplot.yaxis.axis_label = ylabel

# main

curdoc().title = PAGE_TITLE

data_new, data_hosp, data_hosp_uci, data_deaths, data_incidence, data_cfr, data_rt, data_pcr_pos = process_data()

days=len(data_new)

# FIXME get rid of this once we have the complete data
R0=2
x = np.linspace(1, days, days)
source_plot = ColumnDataSource(data=dict(x=x, y=np.full( days, R0)))
####

plot1 = make_plot ('incidence', PLOT1_TITLE, days)
set_plot_details(plot1)

source_plot1 = ColumnDataSource(data=dict(x=x, y=data_incidence))
plot1.line('x', 'y', source=source_plot1, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )

source_plot2 = ColumnDataSource(data=dict(x=x, y=data_pcr_pos))
plot2 = make_plot ('pcr_pos', PLOT2_TITLE, days)
set_plot_details(plot2, 'Days', '%')

plot2.line('x', 'y', source=source_plot2, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )

plot3 = make_plot ('hosp', PLOT3_TITLE, days)
set_plot_details(plot3)

source1_plot3 = ColumnDataSource(data=dict(x=x, y=data_hosp))
source2_plot3 = ColumnDataSource(data=dict(x=x, y=data_hosp_uci))
plot3.line('x', 'y', source=source1_plot3, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )
plot3.line('x', 'y', source=source2_plot3, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR2, )

source_plot4 = ColumnDataSource(data=dict(x=x, y=data_cfr))
plot4 = make_plot ('cfr', PLOT4_TITLE, days)
set_plot_details(plot4, 'Days', '%')

plot4.line('x', 'y', source=source_plot4, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )

plot5 = make_plot ('new', PLOT5_TITLE, days)
set_plot_details(plot5)

source_plot5 = ColumnDataSource(data=dict(x=x, y=data_new))
plot5.line('x', 'y', source=source_plot5, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )

source_plot6 = ColumnDataSource(data=dict(x=x, y=data_deaths))
plot6 = make_plot ('deaths', PLOT6_TITLE, days)
set_plot_details(plot6)

plot6.line('x', 'y', source=source_plot6, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR,  )

plot7 = make_plot ('plot7', PLOT7_TITLE, days)
set_plot_details(plot7)

plot7.line('x', 'y', source=source_plot, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )

source_plot8 = ColumnDataSource(data=dict(x=x, y=data_rt))
plot8 = make_plot ('rt', PLOT8_TITLE, days)
set_plot_details(plot8, 'Days', 'Value')

plot8.line('x', 'y', source=source_plot8, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR,  )

plot9 = make_plot ('plot9', PLOT9_TITLE, days)
set_plot_details(plot9)

plot9.line('x', 'y', source=source_plot, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR,  )

plot10 = make_plot ('plot10', PLOT10_TITLE, days)
set_plot_details(plot10)

plot10.line('x', 'y', source=source_plot, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR,  )

# the layout name is added here then invoked from the HTML template
# all roots added here must be invoked on the GRML

# section 1

layout1 = layout([ [plot1, plot3, plot5, plot7],
                  [plot2, plot4, plot6, plot8] ], 
                   sizing_mode='scale_width', name='section1')

curdoc().add_root(layout1)

# section 2

layout2 = layout([ [plot9, plot10],
                   ], 
                   sizing_mode='scale_width', name='section2')

curdoc().add_root(layout2)
