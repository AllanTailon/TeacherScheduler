#%%
import pandas as pd
import numpy as np
import names
import random
import itertools

def replicate_row(row: pd.Series, times: int) -> pd.DataFrame:
    hora_inicial = pd.to_datetime(row['horario'], format='%H:%M:%S')
    novas_linhas = []
    for i in range(times):
        nova_linha = row.copy()
        nova_linha['horario'] = (hora_inicial + pd.Timedelta(hours=i)).strftime('%H:%M:%S')
        novas_linhas.append(nova_linha)
    return pd.DataFrame(novas_linhas)

def desaninhar_dias(df):
    df['dias da semana'] = df['dias da semana'].str.split(',')
    df = df.explode('dias da semana')
    return df

def expand_rows( df: pd.DataFrame, func) -> pd.DataFrame:
    return pd.concat(df.apply(func, axis=1).tolist(), ignore_index=True)

def clean_data(df: pd.DataFrame)-> pd.DataFrame:

    df['intenviso'] = np.where(df['n aulas']>=10,1,0)

    df['dias da semana'] = df['dias da semana'].str.replace('●',',').str.replace(' ','').str.replace('DOUBLE',',').str.replace('-Triple','').str.split(',')
    df = df.explode('dias da semana').reset_index(drop=True)

    df['dias da semana'] = df['dias da semana'].str.replace('ª','ª,').str.split(',')
    df = df.explode('dias da semana').reset_index(drop=True)

    df = df[df['dias da semana']!=''].copy()

    substituicoes = {
        '2ª': 'SEGUNDA',
        '3ª': 'TERÇA',
        '4ª': 'QUARTA',
        '5ª': 'QUINTA',
        '6ª': 'SEXTA',
        'Saturday': 'SÁBADO'
    }

    df['dias da semana'] = df['dias da semana'].replace(substituicoes, regex=True)

    df['status'].fillna('PRESENCIAL', inplace=True)

    df['horario_tratado'] = pd.to_datetime(df['horario'], format='%H:%M:%S')

    return df

def base_selection(df: pd.DataFrame) -> tuple:
    aulas_tratadas = df.loc[~df['nome grupo'].isnull()]

    aulas = aulas_tratadas.copy()
    # tratando os dados para colocar cada linha uma aula
    aulas['dias da semana'] = aulas['dias da semana'].str.replace('EVERYDAY','2ª ● 3ª ● 4ª ● 5ª ● 6ª')

    # separando as aulas que são triplas, duplas e o resto
    tri = aulas.loc[aulas['dias da semana'] == 'Saturday - Triple']
    doub = aulas.loc[aulas['dias da semana'].str.contains('DOUBLE')]
    aulas_simples = aulas[~aulas['dias da semana'].str.contains('DOUBLE|Saturday - Triple')].copy()

    # tratando a colunas horario
    aulas_simples['horario'] = pd.to_datetime(aulas_simples['horario'],format='%H:%M:%S').dt.strftime('%H:%M:%S')
    return aulas_simples, doub, tri

# %%