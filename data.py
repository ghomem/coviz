import statistics as st
import numpy as np
import pandas as pd
import geopandas as gpd
import glob
import os
import csv
import math
from datetime import datetime

RT_PERIOD = 7   # infections activity period considered for RT
RT_IGNORE = 3   # ignore early days

CFR_DELTA  = 10  # average time to die for CFR calculation
CFR_IGNORE = 30  # ignore early days

INC_PERIOD  = 14    # period for incidence calculations
INC_DIVIDER = 102.8 # to get incidence per 100k people

MAV_PERIOD = 7 # period for moving average calculations

DATA_DIR = '/home/deployment/data/'

# we tolerate isolated one-day or two day holes and make an average of adjacent days
def get_patched_data ( data, delta, fill_initial = False ):

    # skip to the first non None or Nan element
    k = 0
    for value in data:
        if data[k] == None or math.isnan(data[k]):
            if fill_initial:
                data[k] = 0
            k = k + 1
        else:
            break

    length = len(data)
    for j in range (k, len(data)):
        if math.isnan(data[j]) and j+delta < length:
            data[j] = ( ( data[j-delta] + data[j+delta] ) / 2 )

    return data

def get_smooth_list ( data, window_size ):

    series  = pd.Series(data)
    windows = series.rolling(window_size)

    # the first window_size-1 results are nan, but that's OK
    return windows.mean().tolist()

# obtains the new entries from the acumulated entries
def get_differential_series ( data ):

    diff_data = [ 0 ]

    for i, element in enumerate(data):
        if i >= 1:
            diff_data.append( element - data[i-1])

    return diff_data

def get_incidence_T ( data, period, factor ):

    # the first T days have None
    inc_data = list(np.full( period-1, None))

    for i, element in enumerate(data):
        if i >= period-1:
            interval = data [(i-period+1):i]
            value = sum (interval) / factor
            inc_data.append(value)

    return inc_data

# go back period days in time to calculate the cases
def get_cfr ( deaths, new, period, ignore_interval ):

    # the first T days have None value because the numbers are not accurate
    # then we have the user defined interval to ignore and extra rewind days
    # used for averaging the new cases
    fwd = 4
    rew = 3
    cfr_data = list(np.full( period + ignore_interval + rew, None))

    for i, element in enumerate(deaths):
        if i > period + ignore_interval + rew - 1:
            # we smooth the new cases over 7 days around the date
            new_value = st.mean(new[i-period-rew:i-period+fwd])
            if new_value > 0:
                ratio = element / new_value
            else:
                ratio = 0
            cfr_data.append( ratio * 100 )

    # let's smooth now
    result = get_smooth_list(cfr_data, MAV_PERIOD)

    return result

def get_rt ( new, period, ignore_interval ):

    r_data = list(np.full( period + ignore_interval, None))

    for i, element in enumerate(new):
        if i > period + ignore_interval - 1:
            slice = new[i-period:i]
            total = sum(slice)
            r_data.append( new[i] / (total/period) )

    # let's smooth now
    result = get_smooth_list(r_data, MAV_PERIOD)

    return result

def get_positivity ( tests, new, period, ignore_interval ):

    pos_data =  list(np.full( period + ignore_interval, None))

    for i, element in enumerate(tests):
        print(i, element)
        if i > period + ignore_interval - 1:
            num = new[i]
            den = tests[i-period]
            if num and den:
                pos_data.append ( (num / den)*100 )
            else:
                pos_data.append (None)

    # let's smooth now
    result = get_smooth_list(pos_data, MAV_PERIOD)

    return result

# this function is situation specific for the sake of code readability
# returns the average number of deaths in the "same" day of 2015-2019 and the corresponding standard deviation
def get_avg_deaths_2015_2019 (total_deaths, span):

    avg_data = []
    sd_data  = []

    deaths_2015 = total_deaths[    0:365    ] # normal year
    deaths_2016 = total_deaths[  365:730 +1 ] # leap year
    deaths_2017 = total_deaths[  731:1096   ] # normal year
    deaths_2018 = total_deaths[ 1096:1461   ] # normal year
    deaths_2019 = total_deaths[ 1461:1826   ] # normal year

    # should be 365 366 365 365 365 1826
    print ( len (deaths_2015), len(deaths_2016), len(deaths_2017), len(deaths_2018), len(deaths_2019), len(total_deaths) )

    # should be 407 366 475 414 371
    print ( deaths_2015[0], deaths_2016[0], deaths_2017[0], deaths_2018[0], deaths_2019[0] )

    # should be 323 465 390 357 345
    print ( deaths_2015[364], deaths_2016[364], deaths_2017[364], deaths_2018[364], deaths_2019[364] )

    first_day_index = 55 # 26th of February
    for d in range(0,span):
        # idx varies between 0 and 364 (365 values)
        # there could be some long term drift resulting from this code, but only over many years
        idx = d + first_day_index - 365*int( (d + first_day_index) / 365 )
        avg = ( deaths_2015[idx] + deaths_2016[idx] + deaths_2017[idx] + deaths_2018[idx] + deaths_2019[idx] ) / 5
        var = ( (deaths_2015[idx] - avg)**2 + (deaths_2016[idx] - avg)**2 + (deaths_2017[idx] - avg)**2 + (deaths_2018[idx] - avg)**2 + (deaths_2019[idx] - avg)**2 ) / 5
        sd  = math.sqrt(var)
        print(d, idx, avg, sd)

        avg_data.append(avg)
        sd_data.append(sd)

    return avg_data, sd_data

def get_avg_deaths ( total_deaths, span, years ):

    avg_data = []
    sd_data  = []

    data_length=len(total_deaths)
    for d in range(0,span):

        daily_sum = 0
        daily_var_sum = 0

        # we go back 2 years so this is always considering 2015-2019 (pre-Covid)
        for i in range(2, years + 2):
            base_index = data_length-1-span
            # we never let the day index go beyound 365
            day_index = d-365*int(d/365)
            index = base_index-i*365+day_index
            daily_sum = daily_sum + total_deaths[ index ]

        daily_average = daily_sum / years
        avg_data.append( daily_average )

        for i in range(2, years + 2):
            base_index = data_length-1-span
            # we never let the day index go beyound 365
            day_index = d-365*int(d/365)
            index = base_index-i*365+day_index
            daily_var_sum = daily_var_sum + (daily_average - total_deaths[ index ])**2

        daily_sd = math.sqrt( daily_var_sum / years )
        sd_data.append( daily_sd )

        #print(daily_average, daily_sd)

    return avg_data, sd_data

def get_deaths_band ( avg_deaths, sd_deaths ):

    d_inf_data = []
    d_sup_data = []

    for i, element in enumerate(avg_deaths):
        d_inf = element - sd_deaths[i]
        d_sup = element + sd_deaths[i]
        d_inf_data.append(d_inf)
        d_sup_data.append(d_sup)

    return d_inf_data, d_sup_data

def get_dates( date_strings ):

    dates = []
    for d in date_strings:
        dates.append(datetime.strptime(d,'%d-%m-%Y').date())

    return dates

def get_stratified_data ( data, base_str, smoothen, period ):

    data_0_9_f     = data[ base_str + '_0_9_f'    ]
    data_0_9_m     = data[ base_str + '_0_9_m'    ]
    data_10_19_f   = data[ base_str + '_10_19_f'  ]
    data_10_19_m   = data[ base_str + '_10_19_m'  ]
    data_20_29_f   = data[ base_str + '_20_29_f'  ]
    data_20_29_m   = data[ base_str + '_20_29_m'  ]
    data_30_39_f   = data[ base_str + '_30_39_f'  ]
    data_30_39_m   = data[ base_str + '_30_39_m'  ]
    data_40_49_f   = data[ base_str + '_40_49_f'  ]
    data_40_49_m   = data[ base_str + '_40_49_m'  ]
    data_50_59_f   = data[ base_str + '_50_59_f'  ]
    data_50_59_m   = data[ base_str + '_50_59_m'  ]
    data_60_69_f   = data[ base_str + '_60_69_f'  ]
    data_60_69_m   = data[ base_str + '_60_69_m'  ]
    data_70_79_f   = data[ base_str + '_70_79_f'  ]
    data_70_79_m   = data[ base_str + '_70_79_m'  ]
    data_80_plus_f = data[ base_str + '_80_plus_f']
    data_80_plus_m = data[ base_str + '_80_plus_m']

    # we are patching some report holes in the cumulative series using the average value for adjacent days
    data_0_9_total     = get_differential_series( get_patched_data ( (data_0_9_f     + data_0_9_m     ).tolist(), 1, True ) )
    data_10_19_total   = get_differential_series( get_patched_data ( (data_10_19_f   + data_10_19_m   ).tolist(), 1, True ) )
    data_20_29_total   = get_differential_series( get_patched_data ( (data_20_29_f   + data_20_29_m   ).tolist(), 1, True ) )
    data_30_39_total   = get_differential_series( get_patched_data ( (data_30_39_f   + data_30_39_m   ).tolist(), 1, True ) )
    data_40_49_total   = get_differential_series( get_patched_data ( (data_40_49_f   + data_40_49_m   ).tolist(), 1, True ) )
    data_50_59_total   = get_differential_series( get_patched_data ( (data_50_59_f   + data_50_59_m   ).tolist(), 1, True ) )
    data_60_69_total   = get_differential_series( get_patched_data ( (data_60_69_f   + data_60_69_m   ).tolist(), 1, True ) )
    data_70_79_total   = get_differential_series( get_patched_data ( (data_70_79_f   + data_70_79_m   ).tolist(), 1, True ) )
    data_80_plus_total = get_differential_series( get_patched_data ( (data_80_plus_f + data_80_plus_m ).tolist(), 1, True ) )

    tmp_list = [ data_0_9_total, data_10_19_total, data_20_29_total, data_30_39_total, data_40_49_total, data_50_59_total, data_60_69_total, data_70_79_total, data_80_plus_total ]

    data_list = []
    if smoothen:
        for l in tmp_list:
            data_list.append ( get_smooth_list(l, period) )
    else:
        data_list = tmp_list

    return data_list

def get_stratified_cfr ( data, CFR_DELTA, CFR_IGNORE ):

    strat_cv19_new    = get_stratified_data ( data, 'confirmados', False, -1 )
    strat_cv19_deaths = get_stratified_data ( data, 'obitos', False, -1 )

    strat_cfr = []
    for j in range(0, len(strat_cv19_new) ):
        strat_cfr.append( get_cfr(strat_cv19_deaths[j], strat_cv19_new[j], CFR_DELTA, CFR_IGNORE) )

    return strat_cfr

def pad_data ( data, target_size, element, left = True ):

    delta = target_size - len(data)

    # if we don't have enough data we pad with "element"
    if delta >= 0:
        for j in range( target_size - len(data) ):
            if left:
                data.insert(0, element)
            else:
                data.append(element)

    # in case we had more data than wanted we trim it
    return data[:target_size]

def process_data():

    # get the latest of each file type
    files1 = glob.glob(DATA_DIR + 'data-*.csv')
    files2 = glob.glob(DATA_DIR + 'amostras-*.csv')
    files3 = glob.glob(DATA_DIR + 'mortalidade-*.csv')
    files4 = glob.glob(DATA_DIR + 'vacinas-*.csv')

    main_file  = max(files1, key=os.path.getctime)
    tests_file = max(files2, key=os.path.getctime)
    mort_file  = max(files3, key=os.path.getctime)
    vacc_file  = max(files4, key=os.path.getctime)

    main_data  = pd.read_csv(main_file)
    tests_data = pd.read_csv(tests_file)
    mort_data  = pd.read_csv(mort_file)
    vacc_data  = pd.read_csv(vacc_file)

    new          = main_data['confirmados_novos'].tolist()

    # converting the dd-mm-yyyy strings to date objects
    dates        = get_dates(main_data['data'].tolist())

    # the amount of Covid data days that we have
    days         = len(new)

    hosp         = main_data['internados'].tolist()
    hosp_uci     = main_data['internados_uci'].tolist()
    cv19_deaths  = get_differential_series(main_data['obitos'].tolist())
    incidence    = get_incidence_T(new, INC_PERIOD, INC_DIVIDER)
    cfr          = get_cfr(cv19_deaths, new, CFR_DELTA, CFR_IGNORE)
    rt           = get_rt(new, RT_PERIOD, RT_IGNORE)

    # padding the pcr_tests series because it has 2 days of delay it seems - checked on 20/05/2021
    # the padding function also trims it in case it has more data then the other series - checked on 08/10/2021
    pcr_tests    = pad_data( tests_data['amostras_pcr_novas'].tolist(), days, 0, False)
    ag_tests     = pad_data( tests_data['amostras_antigenio_novas'].tolist(), days, 0, False)

    total_tests  = np.add(pcr_tests, ag_tests)
    positivity   = get_positivity( total_tests, new, 2, 0)

    tmp_vacc_part  = vacc_data['pessoas_inoculadas'].interpolate().tolist()
    tmp_vacc_full  = vacc_data['pessoas_vacinadas_completamente'].interpolate().tolist()
    tmp_vacc_boost = vacc_data['pessoas_reforço'].interpolate().tolist()

    # right side padding to compensate the 2 week delay on reporting
    tmp_vacc_part2  = pad_data(tmp_vacc_part,  len(tmp_vacc_part ) +14, None, False)
    tmp_vacc_full2  = pad_data(tmp_vacc_full,  len(tmp_vacc_full ) +14, None, False)
    tmp_vacc_boost2 = pad_data(tmp_vacc_boost, len(tmp_vacc_boost) +14, None, False)

    # left side padding to compensate for vaccination having started later
    vacc_part  = pad_data(tmp_vacc_part2,  days, 0, True)
    vacc_full  = pad_data(tmp_vacc_full2,  days, 0, True)
    # we pad with nan here to avoid a strange overlap effect from the late starting booster doses
    vacc_boost = pad_data(tmp_vacc_boost2, days, np.nan, True)

    # this is a multi year series starting in 01/01/2009
    total_deaths = mort_data['geral_pais'].tolist()

    # note: 2016 is a leap year
    idx1 = mort_data.index[ mort_data['Data'] == '01-01-2015' ][0]
    idx2 = mort_data.index[ mort_data['Data'] == '31-12-2019' ][0] + 1

    total_deaths_precovid = mort_data.iloc[ idx1:idx2 ]['geral_pais'].to_list()

    #print (idx1, idx2)
    #print(total_deaths_precovid)
    #print(len(total_deaths_precovid))

    # we get the average and standard deviation per day
    avg_deaths, sd_deaths = get_avg_deaths_2015_2019(total_deaths_precovid, days)

    avg_deaths_inf, avg_deaths_sup = get_deaths_band ( avg_deaths, sd_deaths )

    # smooth data before presenting
    s_new            = get_smooth_list (new, MAV_PERIOD)
    s_cv19_deaths    = get_smooth_list (cv19_deaths, MAV_PERIOD)
    s_total_deaths   = get_smooth_list (total_deaths[-days:], MAV_PERIOD)
    s_avg_deaths     = get_smooth_list (avg_deaths, MAV_PERIOD)
    s_avg_deaths_inf = get_smooth_list (avg_deaths_inf, MAV_PERIOD)
    s_avg_deaths_sup = get_smooth_list (avg_deaths_sup, MAV_PERIOD)

    # these lists are already smoothed
    s_strat_cv19_new    = get_stratified_data ( main_data, 'confirmados', True, MAV_PERIOD )
    s_strat_cv19_deaths = get_stratified_data ( main_data, 'obitos', True, MAV_PERIOD )

    strat_cfr = get_stratified_cfr ( main_data, CFR_DELTA, CFR_IGNORE )

    # starts at 26th of February of 2020
    print(dates[0], dates[-1])

    return dates, s_new, hosp, hosp_uci, s_cv19_deaths, incidence, cfr, rt, positivity, s_total_deaths, s_avg_deaths, avg_deaths_inf, avg_deaths_sup, s_strat_cv19_new, s_strat_cv19_deaths, strat_cfr, vacc_part, vacc_full, vacc_boost

def get_counties_incidence(row, incidence_data, idx):

    # NAME_2 is the county name (concelho)
    name = row['NAME_2']
    ucase_name = name.upper()

    # handle the only mismatches between the incidence data and the shape file
    if ucase_name == 'PRAIA DA VITÓRIA':
        ucase_name = 'VILA DA PRAIA DA VITÓRIA'

    if ucase_name == 'PONTE DE SÔR':
        ucase_name = 'PONTE DE SOR'

    try:
        # select column and then row
        incidence = incidence_data[ucase_name][idx]
    except:
        print('incidence not found for ' + ucase_name)
        incidence = 0

    #print(ucase_name, incidence)

    return incidence;

def get_incidence_index ( incidence_data, requested_date ):

    # filter by the requested date, using a nearest match

    # get a series with the differences between the requested date and the existing dates
    delta_series = abs( pd.to_datetime(incidence_data['data'], format = '%d-%m-%Y') - pd.to_datetime(requested_date))

    #print(delta_series)

    # find the index of the minimum differnce
    idx = delta_series.idxmin()

    print('index for date', requested_date, 'is', idx, 'and corresponding date is', pd.to_datetime(incidence_data['data'][idx]))

    return idx

# get county incidence list at a certain date
def process_data_counties ( requested_date = None ):

    files1 = glob.glob(DATA_DIR + 'data_concelhos_incidencia-*.csv')

    incidence_file = max(files1, key=os.path.getctime)
    incidence_data = pd.read_csv(incidence_file)

    # retrieves strings from the file
    str_map_date_i = incidence_data['data'].tolist()[0]
    str_map_date_f = incidence_data['data'].tolist()[-1]

    # converts to proper dates
    map_date_i = datetime.strptime(str_map_date_i,'%d-%m-%Y').date()
    map_date_f = datetime.strptime(str_map_date_f,'%d-%m-%Y').date()

    # the default is the latest available date
    if requested_date == None:
        requested_date = map_date_f

    # the shapefile comes from:
    # https://dados.gov.pt/s/resources/concelhos-de-portugal/20181112-193505/concelhos-shapefile.zip

    # we  mention the .shp file but the companion files from the zip must be in the same directory
    poly_file = '/home/deployment/data/shape/concelhos.shp'

    # a GeoDataFrame object is a pandas.DataFrame that has a column with geometry
    # https://geopandas.org/docs/reference/api/geopandas.GeoDataFrame.html
    poly_data = gpd.read_file(poly_file)

    pd.set_option('display.max_rows', None)

    # based on this work
    # https://github.com/jfexbrayat/bokeh-covid/blob/main/bokeh_covid.ipynb

    # let's determine the best index on the incidence vs time table for a requested date
    # that is because data_concelhos_incidencia-*.csv seems to be updated only each 7 days
    # but the pattern is not clear and we must make sure we don't crash
    idx = get_incidence_index ( incidence_data, requested_date )

    # let's add a column with the incidence data for a certain moment in time
    poly_data['incidence'] = poly_data.apply(get_counties_incidence, incidence_data=incidence_data, idx=idx, axis=1)

    # remove the islands
    poly_data = poly_data.loc[ poly_data['NAME_1'] != 'Azores'  ]
    poly_data = poly_data.loc[ poly_data['NAME_1'] != 'Madeira' ]

    #print(poly_data)

    # we return a GeoDataFrame with the counties from the main land, to which an incidence column has been added
    # we also return the first and last dates available from the incidence time series
    return poly_data, map_date_i, map_date_f

#process_data()
#process_data_counties()
