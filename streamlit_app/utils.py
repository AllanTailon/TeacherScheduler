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

def gerar_lista_modulos():
    num_opcoes = random.randint(10, 13)
    
    lista_modulos = [f"Modulo {i}" for i in random.sample(range(1, 14), num_opcoes)]
    
    return lista_modulos

def explode_multiple_columns(df, columns):
    for col in columns:
        df = df.explode(col, ignore_index=True)
    return df

def treat_mock_df(df, columns):
    df_exploded = explode_multiple_columns(df, columns)
    dum_prof = pd.get_dummies(df_exploded, columns=columns)
    prof_treat = dum_prof.groupby('Professor').max().reset_index()
    return prof_treat

def gerar_combinacoes(opcoes):
    todas_combinacoes = []
    for r in range(1, len(opcoes) + 1):
        combinacoes = itertools.combinations(opcoes, r)
        todas_combinacoes.extend(combinacoes)
    return [list(c) for c in todas_combinacoes]

def rand_choice(combinations,sizes,prob):
    escolhas = np.random.choice(len(combinations), size=sizes, p=prob)
    choices = [combinations[i] for i in escolhas]
    return choices

def mock_teach_df(num_professors: int = 50) -> pd.DataFrame:
    
    nomes_distintos = set()  # Usar um conjunto para garantir a distinção
    opcoes_automovel = ["Sim", "Não"]
    opcoes_idioma = ["Ingles", "Espanhol"]
    opcoes_pc = ["Notebook", "Computador"]
    opcoes_unidade = ["Satélite", "Vicentina", "Jardim", "Online"]
    opcoes_disp = ["Manha","Tarde","Noite","Sabado"]

    resultado_comp = gerar_combinacoes(opcoes_pc)
    resultado_unidade = gerar_combinacoes(opcoes_unidade)
    resultado_idioma = gerar_combinacoes(opcoes_idioma)
    resultado_disponibilidade = gerar_combinacoes(opcoes_disp)

    # Gerar as opções para cada característica
    automoveis = list(np.random.choice(opcoes_automovel, size=num_professors, p=[0.7, 0.3]))
    idiomas = rand_choice(resultado_idioma,num_professors,[0.7, 0.1, 0.2])
    computador = rand_choice(resultado_comp,num_professors,[0.4, 0.2, 0.4])
    unidades = rand_choice(resultado_unidade,num_professors,[0]+[0.05] * 12 + [0.2, 0.2])
    disp = rand_choice(resultado_disponibilidade,num_professors,[0]+[0.05] * 12 + [0.2, 0.2])
    modulos = [gerar_lista_modulos() for _ in range(num_professors)]
    
    while len(nomes_distintos) < num_professors:
        primeiro_nome = names.get_first_name()
        nomes_distintos.add(primeiro_nome)
        
    nomes_distintos = list(nomes_distintos)

    info_professors = pd.DataFrame({'Professor': nomes_distintos,
                                    'Unidades':unidades,
                                    'Automovel': automoveis,
                                    'Maquinas': computador,
                                    'disponibilidade':disp,
                                    'Modulo':modulos,
                                    'idiomas':idiomas}
                                    )
    return info_professors
# %%