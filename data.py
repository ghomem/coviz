import statistics as st
import numpy as np
import pandas as pd
import glob
import os
import csv
from datetime import datetime

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
    result = get_smooth_list(cfr_data, 7)

    return result

def get_rt ( new, period, ignore_interval ):

    r_data = list(np.full( period + ignore_interval, None))

    for i, element in enumerate(new):
        if i > period + ignore_interval - 1:
            slice = new[i-period:i]
            total = sum(slice)
            r_data.append( new[i] / (total/period) )

    # let's smooth now
    result = get_smooth_list(r_data, 7)

    return result

def get_pcr_positivity ( pcr_tests, new, period, ignore_interval ):

    pcr_pos_data =  list(np.full( period + ignore_interval, None))

    for i, element in enumerate(pcr_tests):
        if i > period + ignore_interval - 1:
            pcr_pos_data.append ( ( new[i] / pcr_tests[i-period] )*100 )

    # let's smooth now
    result = get_smooth_list(pcr_pos_data, 7)

    return result

def get_avg_deaths ( total_deaths, span, years ):

    avg_data = []

    data_length=len(total_deaths)
    for d in range(0,span):
        daily_sum = 0
        # we go back 2 years so this is always considering 2015-2019 (pre-Covid)
        for i in range(2, years + 2):
            base_index = data_length-1-span
            # we never let the day index go beyound 365
            day_index = d-365*int(d/365)
            index = base_index-i*365+day_index
            daily_sum = daily_sum + total_deaths[ index ]
        avg_data.append(daily_sum / years )

    return avg_data

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

    data_0_9_total     = get_differential_series( ( data_0_9_f     + data_0_9_m     ).tolist())
    data_10_19_total   = get_differential_series( ( data_10_19_f   + data_10_19_m   ).tolist())
    data_20_29_total   = get_differential_series( ( data_20_29_f   + data_20_29_m   ).tolist())
    data_30_39_total   = get_differential_series( ( data_30_39_f   + data_30_39_m   ).tolist())
    data_40_49_total   = get_differential_series( ( data_40_49_f   + data_40_49_m   ).tolist())
    data_50_59_total   = get_differential_series( ( data_50_59_f   + data_50_59_m   ).tolist())
    data_60_69_total   = get_differential_series( ( data_60_69_f   + data_60_69_m   ).tolist())
    data_70_79_total   = get_differential_series( ( data_70_79_f   + data_70_79_m   ).tolist())
    data_80_plus_total = get_differential_series( ( data_80_plus_f + data_80_plus_m ).tolist())

    tmp_list = [ data_0_9_total, data_10_19_total, data_20_29_total, data_30_39_total, data_40_49_total, data_50_59_total, data_60_69_total, data_70_79_total, data_80_plus_total ]

    data_list = []
    if smoothen:
        for l in tmp_list:
            data_list.append ( get_smooth_list(l, period) )
    else:
        data_list = tmp_list

    return data_list

def process_data():

    rt_period = 4   # infections activity period considered for RT
    cfr_delta = 14  # average time to die for CFR calculation

    # get the latest of each file type
    files1 = glob.glob('/home/deployment/data/data-*.csv')
    files2 = glob.glob('/home/deployment/data/amostras-*.csv')
    files3 = glob.glob('/home/deployment/data/mortalidade-*.csv')

    main_file  = max(files1, key=os.path.getctime)
    tests_file = max(files2, key=os.path.getctime)
    mort_file  = max(files3, key=os.path.getctime)

    main_data  = pd.read_csv(main_file)
    tests_data = pd.read_csv(tests_file)
    mort_data  = pd.read_csv(mort_file)

    new          = main_data['confirmados_novos'].tolist()

    # converting the dd-mm-yyyy strings to date objects
    dates        = get_dates(main_data['data'].tolist())

    # the amount of Covid data days that we have
    days         = len(new)

    hosp         = main_data['internados'].tolist()
    hosp_uci     = main_data['internados_uci'].tolist()
    cv19_deaths  = get_differential_series(main_data['obitos'].tolist())
    incidence    = get_incidence_T(new, 14, 102.8)
    cfr          = get_cfr(cv19_deaths, new, cfr_delta, 30) # ignoring early days
    rt           = get_rt(new, rt_period, 4) # ignoring early days
    pcr_tests    = tests_data['amostras_pcr_novas'].tolist()
    pcr_pos      = get_pcr_positivity( pcr_tests, new, 2, 0)

    # this is a multi year series starting in 01/01/2009
    total_deaths = mort_data['geral_pais'].tolist()
    avg_deaths   = get_avg_deaths(total_deaths, days, 5)

    # NOTE the tests series has 2 days of delay it seems - checked on 20/05/2021
    #print(len(cfr), len(rt), len(pcr_tests), len(pcr_pos))

    # smooth data before presenting
    s_new          = get_smooth_list (new, 7)
    s_cv19_deaths  = get_smooth_list (cv19_deaths, 7)
    s_total_deaths = get_smooth_list ( total_deaths[-days:], 7)

    # these lists are already smoothed # TODO
    s_strat_cv19_new    = get_stratified_data ( main_data, 'confirmados', True, 7 )
    s_strat_cv19_deaths = get_stratified_data ( main_data, 'obitos', True, 7 )

    return dates, s_new, hosp, hosp_uci, s_cv19_deaths, incidence, cfr, rt, pcr_pos, s_total_deaths, avg_deaths, s_strat_cv19_new, s_strat_cv19_deaths

#process_data()
