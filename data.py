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

    r_data = list(np.full( period, None))

    for i, element in enumerate(new):
        if i > period + ignore_interval - 1:
            slice = new[i-period:i]
            total = sum(slice)
            r_data.append( new[i] / (total/period) )

    # let's smooth now
    result = get_smooth_list(r_data, 7)

    return result

def process_data():

    files = glob.glob('/home/deployment/data/data-*.csv')
    main_data = max(files, key=os.path.getctime)

    data = pd.read_csv(main_data)

    new       = data['confirmados_novos'].tolist()
    hosp      = data['internados'].tolist()
    hosp_uci  = data['internados_uci'].tolist()
    deaths    = get_differential_series(data['obitos'].tolist())
    incidence = get_incidence_T(new, 14, 102.8)
    cfr       = get_cfr( deaths, new, 14, 30 ) # ignore extra 30 days
    rt        = get_rt(new, 4, 10) # ignore extra 10 days

    return new, hosp, hosp_uci, deaths, incidence, cfr, rt

#process_data()
