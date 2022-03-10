from bokeh.palettes import Inferno256, Magma256, Turbo256, Plasma256, Cividis256, Viridis256, OrRd

PAGE_TITLE = 'Coviz'

PLOT_TOOLS    ='save,reset,pan,wheel_zoom,box_zoom'

PLOT_HEIGHT   = 250 # first section, but the actual height is constrained by the width
PLOT_WIDTH    = 400
PLOT_HEIGHT2  = 145 # for the second section
TEXT_WIDTH    = 500
STATS_WIDTH   = 812
STATS_HEIGHT  = 80
LMARGIN_WIDTH = 20

PLOT_LINE_WIDTH          = 3
PLOT_LINE_WIDTH_CRITICAL = 2

PLOT_LINE_ALPHA       = 0.6
PLOT_LINE_ALPHA_MUTED = 0.1

TITLE_SIZE_HORIZONTAL_LAYOUT = '13pt' # Bokeh default
TITLE_SIZE_VERTICAL_LAYOUT   = '15pt' # For mobile

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
PLOT_LEGEND_FONT_SIZE_VERTICAL_LAYOUT = '15px'

PLOT_LEGEND_SPACING = 0

PLOT1_TITLE  ='14 day Incidence'
PLOT2_TITLE  ='Positivity'
PLOT3_TITLE  ='Hospitalized'
PLOT4_TITLE  ='Case fatality rate'
PLOT5_TITLE  ='New cases'
PLOT6_TITLE  ='Covid deaths'
PLOT7_TITLE  ='Overall deaths'
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
RT_LIMIT         = 1
UCI_LIMIT        = 245 * 5 # multiplied by 5 because we are plotting the series x5

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

TEXT_NOTES  ='<strong>Important:</strong> use the mouse for the initial selection and the cursors for fine tuning.'

# layout related variables
MIN_HORIZONTAL_WIDTH = 1360

PLOT_WIDTH4  = 1240 # for the 4th section
PLOT_HEIGHT4 = 630

