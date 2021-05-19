import statistics as st
import numpy as np
import pandas as pd
import csv

MAIN_DATA='/home/deployment/data/data-2021-05-18.csv'

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

# obtains the new entries from the acumulated entries
def get_differential_series ( data ):

    diff_data = [ 0 ]

    for i, element in enumerate(data):
        if i > 1:
            diff_data.append( element - data[i-1])

    return diff_data

def get_incidence_T ( data, period, factor ):

    # the first T days have 0 value
    inc_data = list(np.full( period, 0))

    for i, element in enumerate(data):
        if i > period:
            interval = data [(i-period-1):i]
            inc_data.append( sum(interval) / factor )

    return inc_data

def process_data():

    data = pd.read_csv(MAIN_DATA)

    new       = data['confirmados_novos'].tolist()
    hosp      = data['internados'].tolist()
    hosp_uci  = data['internados_uci'].tolist()
    deaths    = get_differential_series(data['obitos'].tolist())
    incidence = get_incidence_T(new, 14, 102.8)

    return new, hosp, hosp_uci, deaths, incidence

# this part is only used for CLI testing

print(process_data())
