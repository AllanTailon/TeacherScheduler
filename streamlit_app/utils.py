#%%
import pandas as pd
import numpy as np
import names
import random
import itertools

def replicate_row(row: pd.Series, times: int) -> pd.DataFrame:
    hora_inicial = pd.to_datetime(row['Horário'], format='%H:%M:%S')
    novas_linhas = []
    for i in range(times):
        nova_linha = row.copy()
        nova_linha['Horário'] = (hora_inicial + pd.Timedelta(hours=i)).strftime('%H:%M:%S')
        novas_linhas.append(nova_linha)
    return pd.DataFrame(novas_linhas)

def desaninhar_dias(df):
    df['Dias da Semana'] = df['Dias da Semana'].str.split(',')
    df = df.explode('Dias da Semana')
    return df

def expand_rows( df: pd.DataFrame, func) -> pd.DataFrame:
    return pd.concat(df.apply(func, axis=1).tolist(), ignore_index=True)

def clean_data(df: pd.DataFrame)-> pd.DataFrame:

    df['intenviso'] = np.where(df['N Aulas']>=10,1,0)

    df['Dias da Semana'] = df['Dias da Semana'].str.replace('●',',').str.replace(' ','').str.replace('DOUBLE',',').str.replace('-Triple','').str.split(',')
    df = df.explode('Dias da Semana').reset_index(drop=True)

    df['Dias da Semana'] = df['Dias da Semana'].str.replace('ª','ª,').str.split(',')
    df = df.explode('Dias da Semana').reset_index(drop=True)

    df = df[df['Dias da Semana']!=''].copy()

    substituicoes = {
        '2ª': 'SEGUNDA',
        '3ª': 'TERÇA',
        '4ª': 'QUARTA',
        '5ª': 'QUINTA',
        '6ª': 'SEXTA',
        'Saturday': 'SÁBADO'
    }

    df['Dias da Semana'] = df['Dias da Semana'].replace(substituicoes, regex=True)

    df['STATUS'].fillna('PRESENCIAL', inplace=True)

    df['horario_tratado'] = pd.to_datetime(df['Horário'], format='%H:%M:%S')

    return df

def base_selection(df: pd.DataFrame) -> tuple:
    aulas_tratadas = df.loc[~df['Grupo'].isnull()]

    aulas = aulas_tratadas.copy()
    # tratando os dados para colocar cada linha uma aula
    aulas['Dias da Semana'] = aulas['Dias da Semana'].str.replace('EVERYDAY','2ª ● 3ª ● 4ª ● 5ª ● 6ª')

    # separando as aulas que são triplas, duplas e o resto
    tri = aulas.loc[aulas['Dias da Semana'] == 'Saturday - Triple']
    doub = aulas.loc[aulas['Dias da Semana'].str.contains('DOUBLE')]
    aulas_simples = aulas[~aulas['Dias da Semana'].str.contains('DOUBLE|Saturday - Triple')].copy()

    # tratando a colunas horario
    aulas_simples['Horário'] = pd.to_datetime(aulas_simples['Horário'],format='%H:%M:%S').dt.strftime('%H:%M:%S')
    return aulas_simples, doub, tri

# %%