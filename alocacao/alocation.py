import pandas as pd
from ortools.sat.python import cp_model
from utils import replicate_row,base_selection,expand_rows,clean_data,mock_teach_df
from teacher_alocation import TeacherScheduler

aulas_raw = pd.read_excel('/home/cayena/Downloads/ROTA TESTE CARLOS E ALLAN.xlsx',header=1)

# selecionando aulas simples, duplas e triplas
aulas_simples,doub,tri=base_selection(aulas_raw)

# transformando aulas duplas/triplas em 2/3 linhas
aulas_duplicadas = expand_rows(doub, lambda row: replicate_row(row, times=2))
aulas_triplicadas = expand_rows(tri, lambda row: replicate_row(row, times=3))

# juntando todas as linhas
df_tratado = pd.concat([aulas_simples, aulas_duplicadas, aulas_triplicadas], ignore_index=True)

df_final = clean_data(df_tratado)

info_professors = mock_teach_df(50)

Ts = TeacherScheduler(df_final, info_professors)

base_alocada = Ts.schedule_teachers()
print(base_alocada)