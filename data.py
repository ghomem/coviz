import statistics as st
import numpy as np
import pandas as pd
import geopandas as gpd
import glob
import os
import csv
import math
from datetime import datetime

POPULATION = 10298252

RT_PERIOD = 7   # infections activity period considered for RT
RT_IGNORE = 3   # ignore early days

PREV_PERIOD = RT_PERIOD # we are using the same infectious period for prevalence estimation
PREV_IGNORE = RT_IGNORE # ignore early days

PREV_IMMUNITY_DAYS = 180 # assuming 6 months for the prevalence calculation

CFR_DELTA  = 10  # average time to die for CFR calculation
CFR_IGNORE = 30  # ignore early days

INC_PERIOD  = 14                 # period for incidence calculations
INC_DIVIDER = POPULATION / 10000 # to get incidence per 100k people

MAV_PERIOD = 7 # period for moving average calculations

DATA_DIR = '/home/deployment/coviz-data/'

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

# obtain the minimum prevalence, using the detected cases
def get_min_prevalence ( new, period, ignore_interval, population ):

    r_data = list(np.full( period + ignore_interval, None))

    for i, element in enumerate(new):
        if i > period + ignore_interval - 1:
            slice = new[i-period+1:i+1] # period days, including today
            total = sum(slice)
            min_prevalence = ( total / population)*100
            #print('min', min_prevalence)
            r_data.append( min_prevalence )

    # let's smooth now
    result = get_smooth_list(r_data, MAV_PERIOD)

    return result

# get the worst case scenario for prevalence
def get_max_prevalence (new, min_prevalence, tests, positivity, population):

    r_data = []

    for i, element in enumerate(min_prevalence):
        left_index = max(0, i-PREV_IMMUNITY_DAYS)
        previous_positives = sum( new[  left_index:i] )
        # the population that was tested this day or was previously infected is not part of the potentially infected set
        available_fraction = ( 1 - tests[i]/population - previous_positives/population )
         # worst case scenario positivity % of them could be positive
        extra_prevalence = available_fraction * positivity[i]
        max_prevalence = min_prevalence[i] + extra_prevalence
        r_data.append(max_prevalence)
        #print('max', max_prevalence)

    # let's smooth now
    result = get_smooth_list(r_data, MAV_PERIOD)

    return result


def get_positivity ( tests, new, period, ignore_interval ):

    pos_data =  list(np.full( period + ignore_interval, None))

    for i, element in enumerate(tests):
        #print(i, element)
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

# corrects old overall deaths with the trend due to ageing population
def get_normalized_2020_deaths ( death_array, daily_extra ):

    normalized_death_array = []

    for value in death_array:
        corrected_value = value + daily_extra
        normalized_death_array.append(corrected_value)

    return normalized_death_array

# this function is situation specific for the sake of code readability
# returns the average number of deaths in the "same" day of 2015-2019 and the corresponding standard deviation
def get_avg_deaths_2015_2019 (total_deaths, span, smoothen = False, correct = False):

    avg_data = []
    sd_data  = []

    deaths_2015_in = total_deaths[    0:365    ] # normal year
    deaths_2016_in = total_deaths[  365:730 +1 ] # leap year
    deaths_2017_in = total_deaths[  731:1096   ] # normal year
    deaths_2018_in = total_deaths[ 1096:1461   ] # normal year
    deaths_2019_in = total_deaths[ 1461:1826   ] # normal year

    # when correct is True we are normalizing historical deaths to that equivalent 2020 deaths
    if correct:

        # Fit for overall yearly mortality by Carlos Antunes (x=1 for 2009)
        #   y = 102621 + 966.99x

        # The yearly extra of 966.99 can be converted to a daily extra, 966.99 / 365 = 2.64929
        daily_extra = 2.64929

        deaths_2015 = get_normalized_2020_deaths ( deaths_2015_in, daily_extra * 5 )
        deaths_2016 = get_normalized_2020_deaths ( deaths_2016_in, daily_extra * 4 )
        deaths_2017 = get_normalized_2020_deaths ( deaths_2017_in, daily_extra * 3 )
        deaths_2018 = get_normalized_2020_deaths ( deaths_2018_in, daily_extra * 2 )
        deaths_2019 = get_normalized_2020_deaths ( deaths_2019_in, daily_extra * 1 )
    else:
        deaths_2015 = deaths_2015_in
        deaths_2016 = deaths_2016_in
        deaths_2017 = deaths_2017_in
        deaths_2018 = deaths_2018_in
        deaths_2019 = deaths_2019_in

    # should be 365 366 365 365 365 1826
    #print ( len (deaths_2015), len(deaths_2016), len(deaths_2017), len(deaths_2018), len(deaths_2019), len(total_deaths) )

    # should be 407 366 475 414 371
    #print ( deaths_2015[0], deaths_2016[0], deaths_2017[0], deaths_2018[0], deaths_2019[0] )

    # should be 323 465 390 357 345
    #print ( deaths_2015[364], deaths_2016[364], deaths_2017[364], deaths_2018[364], deaths_2019[364] )

    first_day_index = 55 # 26th of February
    for d in range(0,span):
        # idx varies between 0 and 364 (365 values)
        # there could be some long term drift resulting from this code, but only over many years
        idx = d + first_day_index - 365*int( (d + first_day_index) / 365 )

        # because the period spans more than one year we need additional correction converting 2020 to present year
        if correct:
            delta = daily_extra * int(d/365)
            #print('delta is', delta)
        else:
            delta = 0

        avg = ( deaths_2015[idx] + deaths_2016[idx] + deaths_2017[idx] + deaths_2018[idx] + deaths_2019[idx] + 5*delta ) / 5
        var = ( (deaths_2015[idx] + delta - avg)**2 + (deaths_2016[idx] + delta - avg)**2 + (deaths_2017[idx] + delta - avg)**2 + (deaths_2018[idx] + delta - avg)**2 + (deaths_2019[idx] + delta - avg)**2 ) / 5
        sd  = math.sqrt(var)
        #print(d, idx, avg, sd)

        avg_data.append(avg)
        sd_data.append(sd)

    if smoothen:
        return get_smooth_list( avg_data, MAV_PERIOD ), sd_data
    else:
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

def get_stratified_mortality_info ( mort_data, days ):

    # find the current stratified overall deaths

    # this is a multi year series starting in 01/01/2009
    # we need to get the lastest -days and smoothen for the plots
    # the non-smoothed version will be used for the statistics

    total_deaths_0_1      = mort_data [ 'grupoetario_1ano'      ].tolist()[-days:]
    total_deaths_1_4      = mort_data [ 'grupoetario_1a4anos'   ].tolist()[-days:]
    total_deaths_5_14     = mort_data [ 'grupoetario_5a14anos'  ].tolist()[-days:]
    total_deaths_15_24    = mort_data [ 'grupoetario_15a24anos' ].tolist()[-days:]
    total_deaths_25_34    = mort_data [ 'grupoetario_25a34anos' ].tolist()[-days:]
    total_deaths_35_44    = mort_data [ 'grupoetario_35a44anos' ].tolist()[-days:]
    total_deaths_45_56    = mort_data [ 'grupoetario_45a54anos' ].tolist()[-days:]
    total_deaths_55_64    = mort_data [ 'grupoetario_55a64anos' ].tolist()[-days:]
    total_deaths_65_74    = mort_data [ 'grupoetario_65a74anos' ].tolist()[-days:]
    total_deaths_75_84    = mort_data [ 'grupoetario_75a84anos' ].tolist()[-days:]
    total_deaths_85_plus  = mort_data [ 'grupoetario_85+anos'   ].tolist()[-days:]
    total_deaths_all_ages = mort_data [ 'geral_pais'            ].tolist()[-days:]

    s_total_deaths_0_1        = get_smooth_list ( total_deaths_0_1,        MAV_PERIOD )
    s_total_deaths_1_4        = get_smooth_list ( total_deaths_1_4,        MAV_PERIOD )
    s_total_deaths_5_14       = get_smooth_list ( total_deaths_5_14,       MAV_PERIOD )
    s_total_deaths_15_24      = get_smooth_list ( total_deaths_15_24,      MAV_PERIOD )
    s_total_deaths_25_34      = get_smooth_list ( total_deaths_25_34,      MAV_PERIOD )
    s_total_deaths_35_44      = get_smooth_list ( total_deaths_35_44,      MAV_PERIOD )
    s_total_deaths_45_56      = get_smooth_list ( total_deaths_45_56,      MAV_PERIOD )
    s_total_deaths_55_64      = get_smooth_list ( total_deaths_55_64,      MAV_PERIOD )
    s_total_deaths_65_74      = get_smooth_list ( total_deaths_65_74,      MAV_PERIOD )
    s_total_deaths_75_84      = get_smooth_list ( total_deaths_75_84,      MAV_PERIOD )
    s_total_deaths_85_plus    = get_smooth_list ( total_deaths_85_plus,    MAV_PERIOD )
    s_total_deaths_all_ages   = get_smooth_list ( total_deaths_all_ages,   MAV_PERIOD )

    # now let's find the precovid overal deaths
    # note: 2016 is a leap year
    idx1 = mort_data.index[ mort_data['Data'] == '01-01-2015' ][0]
    idx2 = mort_data.index[ mort_data['Data'] == '31-12-2019' ][0] + 1

    total_deaths_precovid_0_1      = mort_data.iloc[ idx1:idx2 ]['grupoetario_1ano'     ].to_list()
    total_deaths_precovid_1_4      = mort_data.iloc[ idx1:idx2 ]['grupoetario_1a4anos'  ].to_list()
    total_deaths_precovid_5_14     = mort_data.iloc[ idx1:idx2 ]['grupoetario_5a14anos' ].to_list()
    total_deaths_precovid_15_24    = mort_data.iloc[ idx1:idx2 ]['grupoetario_15a24anos'].to_list()
    total_deaths_precovid_25_34    = mort_data.iloc[ idx1:idx2 ]['grupoetario_25a34anos'].to_list()
    total_deaths_precovid_35_44    = mort_data.iloc[ idx1:idx2 ]['grupoetario_35a44anos'].to_list()
    total_deaths_precovid_45_54    = mort_data.iloc[ idx1:idx2 ]['grupoetario_45a54anos'].to_list()
    total_deaths_precovid_55_64    = mort_data.iloc[ idx1:idx2 ]['grupoetario_55a64anos'].to_list()
    total_deaths_precovid_65_74    = mort_data.iloc[ idx1:idx2 ]['grupoetario_65a74anos'].to_list()
    total_deaths_precovid_75_84    = mort_data.iloc[ idx1:idx2 ]['grupoetario_75a84anos'].to_list()
    total_deaths_precovid_85_plus  = mort_data.iloc[ idx1:idx2 ]['grupoetario_85+anos'  ].to_list()
    total_deaths_precovid_all_ages = mort_data.iloc[ idx1:idx2 ]['geral_pais'           ].to_list()

    # we are not smoothing the curve here
    avg_deaths_precovid_0_1,      sd_deaths_precovid_0_1      = get_avg_deaths_2015_2019(total_deaths_precovid_0_1,      days, False)
    avg_deaths_precovid_1_4,      sd_deaths_precovid_1_4      = get_avg_deaths_2015_2019(total_deaths_precovid_1_4,      days, False)
    avg_deaths_precovid_5_14,     sd_deaths_precovid_5_14     = get_avg_deaths_2015_2019(total_deaths_precovid_5_14,     days, False)
    avg_deaths_precovid_15_24,    sd_deaths_precovid_15_24    = get_avg_deaths_2015_2019(total_deaths_precovid_15_24,    days, False)
    avg_deaths_precovid_25_34,    sd_deaths_precovid_25_34    = get_avg_deaths_2015_2019(total_deaths_precovid_25_34,    days, False)
    avg_deaths_precovid_35_44,    sd_deaths_precovid_35_44    = get_avg_deaths_2015_2019(total_deaths_precovid_35_44,    days, False)
    avg_deaths_precovid_45_54,    sd_deaths_precovid_45_54    = get_avg_deaths_2015_2019(total_deaths_precovid_45_54,    days, False)
    avg_deaths_precovid_55_64,    sd_deaths_precovid_55_64    = get_avg_deaths_2015_2019(total_deaths_precovid_55_64,    days, False)
    avg_deaths_precovid_65_74,    sd_deaths_precovid_65_74    = get_avg_deaths_2015_2019(total_deaths_precovid_65_74,    days, False)
    avg_deaths_precovid_75_84,    sd_deaths_precovid_75_84    = get_avg_deaths_2015_2019(total_deaths_precovid_75_84,    days, False)
    avg_deaths_precovid_85_plus,  sd_deaths_precovid_85_plus  = get_avg_deaths_2015_2019(total_deaths_precovid_85_plus,  days, False)
    avg_deaths_precovid_all_ages, sd_deaths_precovid_all_ages = get_avg_deaths_2015_2019(total_deaths_precovid_all_ages, days, False)

    # population ageing corrected reference values
    avg_deaths_precovid_all_ages_c, sd_deaths_precovid_all_ages_c = get_avg_deaths_2015_2019(total_deaths_precovid_all_ages, days, False, True)

    avg_deaths_inf_0_1,        avg_deaths_sup_0_1        = get_deaths_band ( avg_deaths_precovid_0_1,        sd_deaths_precovid_0_1        )
    avg_deaths_inf_1_4,        avg_deaths_sup_1_4        = get_deaths_band ( avg_deaths_precovid_1_4,        sd_deaths_precovid_1_4        )
    avg_deaths_inf_5_14,       avg_deaths_sup_5_14       = get_deaths_band ( avg_deaths_precovid_5_14,       sd_deaths_precovid_5_14       )
    avg_deaths_inf_15_24,      avg_deaths_sup_15_24      = get_deaths_band ( avg_deaths_precovid_15_24,      sd_deaths_precovid_15_24      )
    avg_deaths_inf_25_34,      avg_deaths_sup_25_34      = get_deaths_band ( avg_deaths_precovid_25_34,      sd_deaths_precovid_25_34      )
    avg_deaths_inf_35_44,      avg_deaths_sup_35_44      = get_deaths_band ( avg_deaths_precovid_35_44,      sd_deaths_precovid_35_44      )
    avg_deaths_inf_45_54,      avg_deaths_sup_45_54      = get_deaths_band ( avg_deaths_precovid_45_54,      sd_deaths_precovid_45_54      )
    avg_deaths_inf_55_64,      avg_deaths_sup_55_64      = get_deaths_band ( avg_deaths_precovid_55_64,      sd_deaths_precovid_55_64      )
    avg_deaths_inf_65_74,      avg_deaths_sup_65_74      = get_deaths_band ( avg_deaths_precovid_65_74,      sd_deaths_precovid_65_74      )
    avg_deaths_inf_75_84,      avg_deaths_sup_75_84      = get_deaths_band ( avg_deaths_precovid_75_84,      sd_deaths_precovid_75_84      )
    avg_deaths_inf_85_plus,    avg_deaths_sup_85_plus    = get_deaths_band ( avg_deaths_precovid_85_plus,    sd_deaths_precovid_85_plus    )
    avg_deaths_inf_all_ages,   avg_deaths_sup_all_ages   = get_deaths_band ( avg_deaths_precovid_all_ages,   sd_deaths_precovid_all_ages   )
    avg_deaths_inf_all_ages_c, avg_deaths_sup_all_ages_c = get_deaths_band ( avg_deaths_precovid_all_ages_c, sd_deaths_precovid_all_ages_c )

    # now let's create all the smooth versions

    s_avg_deaths_precovid_0_1        = get_smooth_list( avg_deaths_precovid_0_1,        MAV_PERIOD )
    s_avg_deaths_precovid_1_4        = get_smooth_list( avg_deaths_precovid_1_4,        MAV_PERIOD )
    s_avg_deaths_precovid_5_14       = get_smooth_list( avg_deaths_precovid_5_14,       MAV_PERIOD )
    s_avg_deaths_precovid_15_24      = get_smooth_list( avg_deaths_precovid_15_24,      MAV_PERIOD )
    s_avg_deaths_precovid_25_34      = get_smooth_list( avg_deaths_precovid_25_34,      MAV_PERIOD )
    s_avg_deaths_precovid_35_44      = get_smooth_list( avg_deaths_precovid_35_44,      MAV_PERIOD )
    s_avg_deaths_precovid_45_54      = get_smooth_list( avg_deaths_precovid_45_54,      MAV_PERIOD )
    s_avg_deaths_precovid_55_64      = get_smooth_list( avg_deaths_precovid_55_64,      MAV_PERIOD )
    s_avg_deaths_precovid_65_74      = get_smooth_list( avg_deaths_precovid_65_74,      MAV_PERIOD )
    s_avg_deaths_precovid_75_84      = get_smooth_list( avg_deaths_precovid_75_84,      MAV_PERIOD )
    s_avg_deaths_precovid_85_plus    = get_smooth_list( avg_deaths_precovid_85_plus,    MAV_PERIOD )
    s_avg_deaths_precovid_all_ages   = get_smooth_list( avg_deaths_precovid_all_ages,   MAV_PERIOD )
    s_avg_deaths_precovid_all_ages_c = get_smooth_list( avg_deaths_precovid_all_ages_c, MAV_PERIOD )

    s_avg_deaths_inf_0_1        = get_smooth_list( avg_deaths_inf_0_1,        MAV_PERIOD )
    s_avg_deaths_inf_1_4        = get_smooth_list( avg_deaths_inf_1_4,        MAV_PERIOD )
    s_avg_deaths_inf_5_14       = get_smooth_list( avg_deaths_inf_5_14,       MAV_PERIOD )
    s_avg_deaths_inf_15_24      = get_smooth_list( avg_deaths_inf_15_24,      MAV_PERIOD )
    s_avg_deaths_inf_25_34      = get_smooth_list( avg_deaths_inf_25_34,      MAV_PERIOD )
    s_avg_deaths_inf_35_44      = get_smooth_list( avg_deaths_inf_35_44,      MAV_PERIOD )
    s_avg_deaths_inf_45_54      = get_smooth_list( avg_deaths_inf_45_54,      MAV_PERIOD )
    s_avg_deaths_inf_55_64      = get_smooth_list( avg_deaths_inf_55_64,      MAV_PERIOD )
    s_avg_deaths_inf_65_74      = get_smooth_list( avg_deaths_inf_65_74,      MAV_PERIOD )
    s_avg_deaths_inf_75_84      = get_smooth_list( avg_deaths_inf_75_84,      MAV_PERIOD )
    s_avg_deaths_inf_85_plus    = get_smooth_list( avg_deaths_inf_85_plus,    MAV_PERIOD )
    s_avg_deaths_inf_all_ages   = get_smooth_list( avg_deaths_inf_all_ages,   MAV_PERIOD )
    s_avg_deaths_inf_all_ages_c = get_smooth_list( avg_deaths_inf_all_ages_c, MAV_PERIOD )

    s_avg_deaths_sup_0_1        = get_smooth_list( avg_deaths_sup_0_1,        MAV_PERIOD )
    s_avg_deaths_sup_1_4        = get_smooth_list( avg_deaths_sup_1_4,        MAV_PERIOD )
    s_avg_deaths_sup_5_14       = get_smooth_list( avg_deaths_sup_5_14,       MAV_PERIOD )
    s_avg_deaths_sup_15_24      = get_smooth_list( avg_deaths_sup_15_24,      MAV_PERIOD )
    s_avg_deaths_sup_25_34      = get_smooth_list( avg_deaths_sup_25_34,      MAV_PERIOD )
    s_avg_deaths_sup_35_44      = get_smooth_list( avg_deaths_sup_35_44,      MAV_PERIOD )
    s_avg_deaths_sup_45_54      = get_smooth_list( avg_deaths_sup_45_54,      MAV_PERIOD )
    s_avg_deaths_sup_55_64      = get_smooth_list( avg_deaths_sup_55_64,      MAV_PERIOD )
    s_avg_deaths_sup_65_74      = get_smooth_list( avg_deaths_sup_65_74,      MAV_PERIOD )
    s_avg_deaths_sup_75_84      = get_smooth_list( avg_deaths_sup_75_84,      MAV_PERIOD )
    s_avg_deaths_sup_85_plus    = get_smooth_list( avg_deaths_sup_85_plus,    MAV_PERIOD )
    s_avg_deaths_sup_all_ages   = get_smooth_list( avg_deaths_sup_all_ages,   MAV_PERIOD )
    s_avg_deaths_sup_all_ages_c = get_smooth_list( avg_deaths_sup_all_ages_c, MAV_PERIOD )

    # create the arrays

    # we have a duplication in the last two values to avoid complicating the handling code on main.py
    total_deaths    = [ total_deaths_0_1,   total_deaths_1_4,   total_deaths_5_14,  total_deaths_15_24, total_deaths_25_34, total_deaths_35_44,
                        total_deaths_45_56, total_deaths_55_64, total_deaths_65_74, total_deaths_75_84, total_deaths_85_plus, total_deaths_all_ages, total_deaths_all_ages ]

    # same as above
    s_total_deaths  = [ s_total_deaths_0_1,   s_total_deaths_1_4,   s_total_deaths_5_14,  s_total_deaths_15_24, s_total_deaths_25_34, s_total_deaths_35_44,
                        s_total_deaths_45_56, s_total_deaths_55_64, s_total_deaths_65_74, s_total_deaths_75_84, s_total_deaths_85_plus, s_total_deaths_all_ages, s_total_deaths_all_ages ]

    # on these arrays we have the extra item with the corrected reference values
    avg_deaths      = [ avg_deaths_precovid_0_1,   avg_deaths_precovid_1_4,   avg_deaths_precovid_5_14,  avg_deaths_precovid_15_24, avg_deaths_precovid_25_34, avg_deaths_precovid_35_44,
                        avg_deaths_precovid_45_54, avg_deaths_precovid_55_64, avg_deaths_precovid_65_74, avg_deaths_precovid_75_84, avg_deaths_precovid_85_plus, avg_deaths_precovid_all_ages, avg_deaths_precovid_all_ages_c ]

    avg_deaths_inf = [ avg_deaths_inf_0_1,   avg_deaths_inf_1_4,   avg_deaths_inf_5_14,  avg_deaths_inf_15_24, avg_deaths_inf_25_34,   avg_deaths_inf_35_44,
                       avg_deaths_inf_45_54, avg_deaths_inf_55_64, avg_deaths_inf_65_74, avg_deaths_inf_75_84, avg_deaths_inf_85_plus, avg_deaths_inf_all_ages, avg_deaths_inf_all_ages_c ]

    avg_deaths_sup = [ avg_deaths_sup_0_1,   avg_deaths_sup_1_4,   avg_deaths_sup_5_14,  avg_deaths_sup_15_24, avg_deaths_sup_25_34,   avg_deaths_sup_35_44,
                       avg_deaths_sup_45_54, avg_deaths_sup_55_64, avg_deaths_sup_65_74, avg_deaths_sup_75_84, avg_deaths_sup_85_plus, avg_deaths_sup_all_ages, avg_deaths_sup_all_ages_c ]


    s_avg_deaths      = [ s_avg_deaths_precovid_0_1,   s_avg_deaths_precovid_1_4,   s_avg_deaths_precovid_5_14,  s_avg_deaths_precovid_15_24, s_avg_deaths_precovid_25_34, s_avg_deaths_precovid_35_44,
                        s_avg_deaths_precovid_45_54, s_avg_deaths_precovid_55_64, s_avg_deaths_precovid_65_74, s_avg_deaths_precovid_75_84, s_avg_deaths_precovid_85_plus, s_avg_deaths_precovid_all_ages, s_avg_deaths_precovid_all_ages_c ]

    s_avg_deaths_inf = [ s_avg_deaths_inf_0_1,   s_avg_deaths_inf_1_4,   s_avg_deaths_inf_5_14,  s_avg_deaths_inf_15_24, s_avg_deaths_inf_25_34,   s_avg_deaths_inf_35_44,
                       s_avg_deaths_inf_45_54, s_avg_deaths_inf_55_64, s_avg_deaths_inf_65_74, s_avg_deaths_inf_75_84, s_avg_deaths_inf_85_plus, s_avg_deaths_inf_all_ages, s_avg_deaths_inf_all_ages_c ]

    s_avg_deaths_sup = [ s_avg_deaths_sup_0_1,   s_avg_deaths_sup_1_4,   s_avg_deaths_sup_5_14,  s_avg_deaths_sup_15_24, s_avg_deaths_sup_25_34,   s_avg_deaths_sup_35_44,
                       s_avg_deaths_sup_45_54, s_avg_deaths_sup_55_64, s_avg_deaths_sup_65_74, s_avg_deaths_sup_75_84, s_avg_deaths_sup_85_plus, s_avg_deaths_sup_all_ages, s_avg_deaths_sup_all_ages_c ]

    strat_mort_info = [ total_deaths, s_total_deaths, avg_deaths, avg_deaths_inf, avg_deaths_sup, s_avg_deaths, s_avg_deaths_inf, s_avg_deaths_sup ]

    return strat_mort_info

def get_stratified_cfr ( data, CFR_DELTA, CFR_IGNORE, maxlen ):

    strat_cv19_new    = get_stratified_data ( data, 'confirmados', False, -1 )
    strat_cv19_deaths = get_stratified_data ( data, 'obitos', False, -1 )

    strat_cfr = []
    for j in range(0, len(strat_cv19_new) ):
        my_cfr = get_cfr(strat_cv19_deaths[j], strat_cv19_new[j], CFR_DELTA, CFR_IGNORE)
        my_len = len(strat_cv19_new[j])

        # helper variable to set the last part to None instead of zero
        empty_list = np.full( my_len - maxlen , None)

        # important: this assignement conserves the list size
        my_cfr[maxlen:-1] = np.full( my_len - maxlen - 1 , None)

        strat_cfr.append( my_cfr )

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

def get_days_until_patch ( data ):

    idx = np.where(~np.isnan(data))[-1][-1]

    # the number of days is the index plus 1
    return idx + 1

def get_data():

    # get the latest of each file type
    main_file     = DATA_DIR + 'merged/data.csv'
    tests_file    = DATA_DIR + 'merged/amostras.csv'
    mort_file     = DATA_DIR + 'dssg/mortalidade.csv'
    vacc_file     = DATA_DIR + 'dssg/vacinas.csv'
    vacc_cfr_file = DATA_DIR + 'custom/CFR-vs-status.csv'
    vacc_chr_file = DATA_DIR + 'custom/CHR-vs-status.csv'

    main_data     = pd.read_csv(main_file)
    tests_data    = pd.read_csv(tests_file)
    mort_data     = pd.read_csv(mort_file)
    vacc_data     = pd.read_csv(vacc_file)
    vacc_cfr_data = pd.read_csv(vacc_cfr_file)
    vacc_chr_data = pd.read_csv(vacc_chr_file)

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
    total_tests  = pad_data( tests_data['amostras_novas'].tolist(), days, 0, False)
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

    # unfortunately the stratified data was interrupted
    # this is a helper variable that prevents CFR artifacts
    days2 = get_days_until_patch ( s_strat_cv19_new[0] )

    strat_cfr = get_stratified_cfr ( main_data, CFR_DELTA, CFR_IGNORE, days2 )

    # get age stratified mortality information
    # average precovid deaths and respective standard deviation bands, plus smoothed current overall deaths
    # this is an age stratified generalization of what we have already done with the total for all ages
    strat_mortality_info = get_stratified_mortality_info( mort_data, days )

    # starts at 26th of February of 2020
    #print(dates[0], dates[-1])

    s_min_prevalence = get_min_prevalence (new, PREV_PERIOD, PREV_IGNORE, POPULATION)
    s_max_prevalence = get_max_prevalence (new, s_min_prevalence, total_tests, positivity, POPULATION)
    s_avg_prevalence = 0.5 * ( np.array(s_min_prevalence) + np.array(s_max_prevalence) )

    # processed data
    processed_data = [ s_new, hosp, hosp_uci, s_cv19_deaths, incidence, cfr, rt, positivity, s_total_deaths, s_avg_deaths,\
                    avg_deaths_inf, avg_deaths_sup, s_strat_cv19_new, s_strat_cv19_deaths, strat_cfr, vacc_part, vacc_full,\
                    vacc_boost, strat_mortality_info, s_min_prevalence, s_max_prevalence, s_avg_prevalence, vacc_cfr_data, vacc_chr_data ]

    # raw data for stats
    raw_data = [ new, cv19_deaths, total_deaths[-days:], avg_deaths ]

    return dates, processed_data, raw_data

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
def get_data_counties ( requested_date = None ):

    incidence_file = DATA_DIR + 'dssg/data_concelhos_incidencia.csv'
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

