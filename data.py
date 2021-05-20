import statistics as st
import numpy as np
import pandas as pd
import glob
import os
import csv

#data_dados
#confirmados
#confirmados_arsnorte
#confirmados_arscentro
#confirmados_arslvt
#confirmados_arsalentejo
#confirmados_arsalgarve
#confirmados_acores
#confirmados_madeira
#confirmados_estrangeiro
#confirmados_novos
#recuperados
#obitos
#internados
#internados_uci
#lab
#suspeitos
#vigilancia
#n_confirmados
#cadeias_transmissao
#transmissao_importada
#confirmados_0_9_f
#confirmados_0_9_m
#confirmados_10_19_f
#confirmados_10_19_m
#confirmados_20_29_f
#confirmados_20_29_m
#confirmados_30_39_f
#confirmados_30_39_m
#confirmados_40_49_f
#confirmados_40_49_m
#confirmados_50_59_f
#confirmados_50_59_m
#confirmados_60_69_f
#confirmados_60_69_m
#confirmados_70_79_f
#confirmados_70_79_m
#confirmados_80_plus_f
#confirmados_80_plus_m
#sintomas_tosse
#sintomas_febre
#sintomas_dificuldade_respiratoria
#sintomas_cefaleia
#sintomas_dores_musculares
#sintomas_fraqueza_generalizada
#confirmados_f
#confirmados_m
#obitos_arsnorte
#obitos_arscentro
#obitos_arslvt
#obitos_arsalentejo
#obitos_arsalgarve
#obitos_acores
#obitos_madeira
#obitos_estrangeiro
#recuperados_arsnorte
#recuperados_arscentro
#recuperados_arslvt
#recuperados_arsalentejo
#recuperados_arsalgarve
#recuperados_acores
#recuperados_madeira
#recuperados_estrangeiro
#obitos_0_9_f
#obitos_0_9_m
#obitos_10_19_f
#obitos_10_19_m
#obitos_20_29_f
#obitos_20_29_m
#obitos_30_39_f
#obitos_30_39_m
#obitos_40_49_f
#obitos_40_49_m
#obitos_50_59_f
#obitos_50_59_m
#obitos_60_69_f
#obitos_60_69_m
#obitos_70_79_f
#obitos_70_79_m
#obitos_80_plus_f
#obitos_80_plus_m
#obitos_f
#obitos_m
#confirmados_desconhecidos_m
#confirmados_desconhecidos_f
#ativos
#internados_enfermaria
#confirmados_desconhecidos
#incidencia_nacional
#incidencia_continente
#rt_nacional
#rt_continente

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
            inc_data.append( sum(interval) / factor )

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
        for i in range(1, years + 1 ):
            base_index = data_length-1-span
            index = base_index-i*365+d
            print (d,i, index, index > data_length)
            daily_sum = daily_sum + total_deaths[ index ]
        avg_data.append(daily_sum / years )

    return avg_data

def process_data():

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

    # the amount of Covid data days that we have
    days         = len(new)

    hosp         = main_data['internados'].tolist()
    hosp_uci     = main_data['internados_uci'].tolist()
    cv19_deaths  = get_differential_series(main_data['obitos'].tolist())
    incidence    = get_incidence_T(new, 14, 102.8)
    cfr          = get_cfr(cv19_deaths, new, 14, 30 ) # ignore extra days
    rt           = get_rt(new, 4, 4) # ignore extra days
    pcr_tests    = tests_data['amostras_pcr_novas'].tolist()
    pcr_pos      = get_pcr_positivity( pcr_tests, new, 2, 0 )

    # this is a multi year series starting in 01/01/2009
    total_deaths = mort_data['geral_pais'].tolist()
    avg_deaths   = get_avg_deaths(total_deaths, days, 5)

    # TODO a analise das amostras tem dois dias de atraso
    print(len(cfr), len(rt), len(pcr_tests), len(pcr_pos))

    s_new = get_smooth_list (new, 7)
    s_cv19_deaths = get_smooth_list (cv19_deaths, 7)
    s_total_deaths = get_smooth_list ( total_deaths[-days:], 7 )

    return s_new, hosp, hosp_uci, s_cv19_deaths, incidence, cfr, rt, pcr_pos, s_total_deaths, avg_deaths

#process_data()
