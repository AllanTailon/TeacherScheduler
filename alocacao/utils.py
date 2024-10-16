import pandas as pd
import numpy as np
import names

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

    df['Dias da Semana'] = df['Dias da Semana'].str.replace('●',',').str.replace(' ','').str.split(',')
    df = df.explode('Dias da Semana').reset_index(drop=True)

    df['Dias da Semana'] = df['Dias da Semana'].str.replace('ª','ª,').str.split(',')
    df = df.explode('Dias da Semana').reset_index(drop=True)

    df = df[df['Dias da Semana']!=''].copy()

    df['STATUS'].fillna('PRESENCIAL', inplace=True)

    df['horario_tratado'] = pd.to_datetime(df['Horário'], format='%H:%M:%S')

    return df

def base_selection(df: pd.DataFrame) -> tuple:
    aulas_tratadas = df.loc[~df['Grupo'].isnull()][['Grupo','Horário','Dias da Semana','Unidade','STATUS','MOD']]
    aulas_tratadas = aulas_tratadas.loc[aulas_tratadas['Dias da Semana']!='FOLDER'].reset_index(drop=True)

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

def mock_teach_df(num_professors: int = 50) -> pd.DataFrame:
    nomes_distintos = set()  # Usar um conjunto para garantir a distinção
    tem_carro = list(np.random.choice([0, 1], size=num_professors, p=[0.3, 0.7]))
    espanhol = list(np.random.choice([0, 1], size=num_professors, p=[0.8, 0.2]))
    tem_pc = list(np.random.choice([0, 1], size=num_professors, p=[0.2, 0.8]))

    while len(nomes_distintos) < num_professors:
        primeiro_nome = names.get_first_name()
        nomes_distintos.add(primeiro_nome)
        
    nomes_distintos = list(nomes_distintos)

    info_professors = pd.DataFrame({'professor': nomes_distintos, 'tem_carro': tem_carro, 'fala_espanhol': espanhol, 'tem_pc': tem_pc})
    return info_professors

