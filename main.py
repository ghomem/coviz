import numpy as np

from bokeh.io import curdoc
from bokeh.layouts import layout
from bokeh.models import Button, CategoricalColorMapper, ColumnDataSource, HoverTool, Label, SingleIntervalTicker, Slider
from bokeh.palettes import Spectral6
from bokeh.plotting import figure

PAGE_TITLE = 'Coviz'

PLOT_TOOLS    ='save,reset,pan,wheel_zoom,box_zoom'

PLOT_HEIGHT   = 250
PLOT_WIDTH    = 500
TEXT_WIDTH    = 300
LMARGIN_WIDTH = 20

PLOT_LINE_WIDTH = 3
PLOT_LINE_ALPHA = 0.6

PLOT_X_LABEL  = 'Days'
PLOT_Y_LABEL  = 'Count'
PLOT_Y_LABEL2 = 'Value'

PLOT_LINE_COLOR = 'gray'

PLOT1_TITLE  ='14 Day incidence'
PLOT2_TITLE  ='PCR Positivity'
PLOT3_TITLE  ='Hospitalized, UCI'
PLOT4_TITLE  ='Case fatality rate'
PLOT5_TITLE  ='New cases'
PLOT6_TITLE  ='New cases by age group'
PLOT7_TITLE  ='Mortality (Covid, 5y avg, total)'
PLOT8_TITLE  ='Rt'
PLOT9_TITLE  ='New cases por per group'
PLOT10_TITLE ='Not sure either'

DAYS=720

def make_plot( name, title ):
    return figure(plot_height=PLOT_HEIGHT, plot_width=PLOT_WIDTH, title=title, tools=PLOT_TOOLS, x_range=[0, DAYS], name=name)

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

# FIXME get real data for this
R0=2
x = np.linspace(1, DAYS, DAYS)
source_plot = ColumnDataSource(data=dict(x=x, y=np.full( DAYS, R0)))
####

plot1 = make_plot ('plot1', PLOT1_TITLE)
plot1.line('x', 'y', source=source_plot, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )
set_plot_details(plot1)

plot2 = make_plot ('plot2', PLOT2_TITLE)
plot2.line('x', 'y', source=source_plot, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )
set_plot_details(plot2, 'Days', '%')

plot3 = make_plot ('plot3', PLOT3_TITLE)
plot3.line('x', 'y', source=source_plot, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )
set_plot_details(plot3)

plot4 = make_plot ('plot4', PLOT4_TITLE)
plot4.line('x', 'y', source=source_plot, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )
set_plot_details(plot4, 'Days', '%')

plot5 = make_plot ('plot5', PLOT5_TITLE)
plot5.line('x', 'y', source=source_plot, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )
set_plot_details(plot5)

plot6 = make_plot ('plot6', PLOT6_TITLE)
plot6.line('x', 'y', source=source_plot, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR,  )
set_plot_details(plot6)

plot7 = make_plot ('plot7', PLOT7_TITLE)
plot7.line('x', 'y', source=source_plot, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR, )
set_plot_details(plot7)

plot8 = make_plot ('plot8', PLOT8_TITLE)
plot8.line('x', 'y', source=source_plot, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR,  )
set_plot_details(plot8, 'Days', 'Value')

plot9 = make_plot ('plot9', PLOT9_TITLE)
plot9.line('x', 'y', source=source_plot, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR,  )
set_plot_details(plot9)

plot10 = make_plot ('plot10', PLOT10_TITLE)
plot10.line('x', 'y', source=source_plot, line_width=PLOT_LINE_WIDTH, line_alpha=PLOT_LINE_ALPHA, line_color=PLOT_LINE_COLOR,  )
set_plot_details(plot10)


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
