from bokeh.palettes import Inferno256, Magma256, Turbo256, Plasma256, Cividis256, Viridis256, OrRd

PAGE_TITLE = 'Coviz'

PLOT_TOOLS    = 'save,reset,pan,wheel_zoom,box_zoom'

PLOT_HEIGHT   = 250  # first section, but the actual height is constrained by the width
PLOT_WIDTH    = 400
PLOT_HEIGHT2  = 145  # for the second section
TEXT_WIDTH    = 500
STATS_WIDTH   = 812
STATS_HEIGHT  = 80
LMARGIN_WIDTH = 20

PLOT_LINE_WIDTH          = 3
PLOT_LINE_WIDTH_CRITICAL = 2

PLOT_LINE_ALPHA       = 0.6
PLOT_LINE_ALPHA2      = 0.9
PLOT_LINE_ALPHA_MUTED = 0.1

TITLE_SIZE_HORIZONTAL_LAYOUT = '13pt'  # Bokeh default
TITLE_SIZE_VERTICAL_LAYOUT   = '15pt'  # For mobile

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

PLOT1_TITLE  = '14 day Incidence'
PLOT2_TITLE  = 'Positivity'
PLOT3_TITLE  = 'Hospitalized'
PLOT4_TITLE  = 'Case fatality rate'
PLOT5_TITLE  = 'New cases'
PLOT6_TITLE  = 'Covid deaths'
PLOT7_TITLE  = 'Overall deaths'
PLOT8_TITLE  = 'Rt'
PLOT9_TITLE  = 'New cases by age group (click on the legend to hide/show series)'
PLOT10_TITLE = 'Covid deaths by age group (click on the legend to hide/show series)'
PLOT11_TITLE = 'CFR by age group (click on the legend to hide/show series)'
PLOT12_TITLE = 'Vaccination'

PLOT_CORRELATION_TITLE = 'Excess deaths vs Covid deaths'
PLOT_PREVALENCE_TITLE  = 'Prevalence envelope'

VACC_CFR_TITLE = 'Case fatality rate (CFR) by vaccination status'
VACC_CHR_TITLE = 'Case hospitalization rate (CHR) by vaccination status'

CLINES_LABEL = 'Show limits'
CLINES_SWITCH_WIDTH = 140
CLINES_SWITCH_HEIGHT = 30

# epidemic management red lines

INCIDENCE_LIMIT  = 120
POSITIVITY_LIMIT = 4
RT_LIMIT         = 1
UCI_LIMIT        = 245 * 5  # multiplied by 5 because we are plotting the series x5

DATE_IGNORE = 15

# map related

MAP_INCIDENCE_MIN = 0
MAP_INCIDENCE_MAX = 1600
MAP_INCIDENCE_RESOLUTION = 9  # min 3, max 9

MAP_WIDTH  = 454
MAP_HEIGHT = 605

# in meters, eg, 1000 -> 1km
MAP_RESOLUTION = 1500

MAP_TILE_PROVIDER = None

MAP_TITLE = '14 day Incidence per county'

TEXT_NOTES = '<strong>Important:</strong> use the mouse for the initial selection and the cursors for fine tuning.'

# layout related variables
MIN_HORIZONTAL_WIDTH = 1360

PLOT_WIDTH4  = 900  # for the 4th section
PLOT_HEIGHT4 = 475

PLOT_AREAS_COLOR4 = 'gray'
PLOT_AREAS_ALPHA4 = 0.1

MORT_STATS_TABLE_WIDTH  = 490
MORT_STATS_TABLE_HEIGHT = 355

MORT_TEXT_WIDTH = 480

PLOT_WIDTH5  = 900  # for the 5th section
PLOT_HEIGHT5 = 505

P_HEADING_STYLE = "font-size: 140%; font-weight: bold; padding-top: 7px; padding-bottom: 5px; margin-bottom: 0px; color: #4d4d4d"
P_TEXT_STYLE    = "font-size: 100%; font-weight: normal; padding-top: 7px; color: #4d4d4d"
P_TEXT_STYLE_L  = "font-size: 110%; font-weight: normal; padding-top: 7px; color: #4d4d4d"

PREV_TEXT_WIDTH = 410
PREV_TEXT = f"""<div class="content" style="padding-top: 10px;">
                <p style="{P_HEADING_STYLE}">
                    The prevalence envelope
                </p>
                <p style="{P_TEXT_STYLE}">
                    How many people are infected with Covid in a given moment in time?</br></br>
                    It is not possible to provide reliable prevalence estimations without a mass testing policy or at least periodic testing of significant population samples.\
                    However, the amount of testing and the testing strategy have changed significantly over time. We present the prevalence envelope that can be derived from the existing data.</br></br>\
                    The plot on the left displays very crude best-case (Min prevalence) and worst case (Max prevalence) scenarios, along with an average of those two.</br></br>\
                    The best case scenario considers that the prevalence is the sum of cases found in the last 7 days (including today).
                    The worst case scenario adds, as extra prevalance, the part of population that was not tested today, minus those who were
                    found to be infected in the previous 180 days, multiplied by the positivity.
                </p>
            </div>"""

PLOT_WIDTH6  = 505  # for the 6th section
PLOT_HEIGHT6 = 505

VACC_RISK_TEXT_WIDTH = 410

VACC_RISK_TEXT = f"""<div class="content" style="padding-top: 15px;">
                   <p style="{P_HEADING_STYLE}">
                    The effect of vaccines
                  </p>
                  <p style="{P_TEXT_STYLE}">
                      How does vaccination affect the risk of hospitalization and death?</br></br>
                      The answer to this question is rather complex as it depends on vaccinating timing, rythm, immunity waning and
                      interaction of vaccines with new virus variants. One pragmatic data driven approach is looking into the Case Fatality Rate (CFR)
                      and Case Hospitalization Rate (CHR) broken down by vaccination status and age group.</br></br>
                      This information is made available by the health authority on a PDF containing data for a single month. The values
                      present on the plots were assembled from all the PDFs that were published so far.</br></br>
                      <b>Note: </b>to our best knowledge, data for September 2021 has not been published.
                </p>
            </div>"""

FINAL_TEXT_WIDTH = 410

FINAL_TEXT = f"""<div class="content" style="padding-top: 15px; margin-bottom: 20px">

                    <p style="{P_HEADING_STYLE}">
                        About Coviz
                    </p>

                    <p style="{P_TEXT_STYLE_L}">
                        This website started as an improved version of the public Covid dashboard. The initial idea
                        was providing better layouts, that allowed for simultaneous inpection of related quantities.
                        It then evolved in the direction of providing data from different public data sources (ex: age stratified overall mortality).

                        Meanwhile, our health authority (DGS) retired the original dashboard reducing official daily reporting to
                        "fluid-named" excel files, and making Coviz the only place where a data driven story of the pandemic in
                        Portugal can be found.
                        </br></br>
                        As of 13/03/2022 DGS reduced the scope of reporting, preventing the geospatial and
                        age-stratified plots from being updated. As of 01/06/2022 the information about testing stopped being reported,
                        forcing the retrieval if such data from ECDC\'s files. The information from DGS is not downloadable from
                        cloud instances (including pipeline runners) due to enforced geographical restrictions, making it difficult
                        for interested citizens to transform, study and visualize data that in essence belongs to them. While this project
                        intends to restore the level of transparency that the portuguese citizens deserve, it is not an official source of
                        information and we can not garantee that the result is error free. Should any problems be found, they can be reported at the project\'s Github page.
                        </br></br>
                        Most data is presented as a 7 day moving average to make reading the plots easier. The goal of this dashboard is allowing the
                        visualization of mid term trends rather than the short term noise.
                    </p>

                    <p style="{P_HEADING_STYLE}">
                        Credits
                    </p>

                    <p style="{P_TEXT_STYLE_L}">
                        The source code for this application can be found <a target="_blank" href="https://github.com/ghomem/coviz/">here</a>.<br/>
                        The web frontend loads in Portable Web App (PWA) mode thanks to the <a target="_blank" href="https://github.com/pmac-dev/coviz-pwa">contribution </a> of <a target="_blank" href="https://github.com/pmac-dev/coviz-pwa">@pmac-dev</a>.</br>
                        The static content was adapted from <a target="_blank" href="https://html5up.net/story">HTML5UP</a>.<br/>
                        The plots are made with <a target="_blank" href="https://bokeh.org">Bokeh</a>.<br/>
                        Historical data was obtained from the <a target="_blank" href="https://github.com/dssg-pt/">DSSG-PT</a> repositories and current data is merged from DGS, DSSG-PT and ECDC data sources.
                    </p>

                    <p style="{P_HEADING_STYLE}">
                        Resources
                    </p>

                    <p style="{P_TEXT_STYLE_L}">
                        The parent project of this dashboard can be found <a target="_blank" href="https://github.com/ghomem/pandemic-toolkit/">here</a>.
                    </p>
                </div>"""
