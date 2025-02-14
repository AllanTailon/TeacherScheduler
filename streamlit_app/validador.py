import pandas as pd
import numpy as np

class validador:

    def __init__(self, df_class, df_teach):

        self.df_class = df_class
        self.df_teach = df_teach
        self.teacher_alocated = self.df_class[((self.df_class['teacher']!='-')&(self.df_class['teacher'].notnull()))]['teacher'].unique()

    def check_existent_teacher(self):
        """
        Check if there are teachers in the class that are not in the teacher table
        """
        teachers_pre_alocado = self.df_class[((self.df_class['teacher'].notnull())&(self.df_class['teacher']!='-'))]['teacher'].unique()
        teachers = self.df_teach['TEACHER'].unique()
        diff = set(teachers_pre_alocado) - set(teachers)
        if diff:
            print(f'Teachers not found in the teacher table: {diff}')

    def check_existent_hour(self):
        """
        Check if there are hours in the class that are not in the teacher table
        """
        horas_aula = self.df_class['horario'].unique()
        colunas = self.df_teach.columns
        diff = set(horas_aula) - set(colunas)
        turmas_diff = self.df_class[self.df_class['horario'].isin(diff)]['nome grupo'].unique()
        if diff:
            print(f'Hours not found in the teacher table: {diff} for the classes: {turmas_diff}')
            

    def check_possible_time(self):
        """
        Check if the hours in the class are possible
        """
        horarios_nao_permitido = {}
        dia_da_semana_nao_permitido = {}

        for professor in self.teacher_alocated:
            horarios = self.df_class[self.df_class['teacher']==professor]['horario'].unique()
            dia_semana = self.df_class[self.df_class['teacher']==professor]['dias da semana'].unique()

            prof_horarios = self.df_teach[self.df_teach['TEACHER']==professor][horarios]
            prof_diasemana = self.df_teach[self.df_teach['TEACHER']==professor][dia_semana]

            erros_horario = prof_horarios.columns[(prof_horarios == 0).any()].to_list()
            erros_diasemana = prof_diasemana.columns[(prof_diasemana == 0).any()].to_list()

            if erros_horario:
                horarios_nao_permitido[professor] = erros_horario
            if erros_diasemana:
                dia_da_semana_nao_permitido[professor] = erros_diasemana

        if horarios_nao_permitido:
            print("Horários não permitidos para os professores:")
            print(horarios_nao_permitido)
        if dia_da_semana_nao_permitido:
            print("Dia da semana não permitidos para os professores:")
            print(dia_da_semana_nao_permitido)
    
    def check_multiple_classes(self):
        """
        Check if there are multiple classes in the same hour
        """
        for professor in self.teacher_alocated:
            for diasemana in self.df_class[self.df_class['teacher']==professor]['dias da semana'].unique():
                for horario in self.df_class[self.df_class['teacher']==professor]['horario'].unique():
                    turmas = self.df_class[(self.df_class['teacher']==professor)&(self.df_class['dias da semana']==diasemana)&(self.df_class['horario']==horario)]['nome grupo'].unique()
                    if len(turmas)>1:
                        print(f'Teacher {professor} has multiple classes in the same hour: {turmas}')
    
    def check_modality_group(self):
        """
        
        """ 
        modalidades = self.df_class[self.df_class['modalidade']!='Inglês']['modalidade'].unique()
        grupo = self.df_class['grupo'].unique()

        colunas_prof = self.df_teach.columns
        diff_mod = set(modalidades) - set(colunas_prof)
        diff_grupo = set(grupo) - set(colunas_prof)
        aulas_mod = self.df_class[self.df_class['modalidade'].isin(diff_mod)]['nome grupo'].unique()
        aulas_grupo = self.df_class[self.df_class['grupo'].isin(diff_grupo)]['nome grupo'].unique()
        if diff_mod:
            print(f'Modalities not found in the teacher table: {diff_mod} para a seguintes turmas: {aulas_mod}')
        if diff_grupo:
            print(f'Groups not found in the teacher table: {diff_grupo} para a seguintes turmas: {aulas_grupo}')

    def check_teach_status(self):
        """
        Check if the teacher is active
        """
        for i in self.teacher_alocated:
            if i in self.df_teach['TEACHER'].unique():
                status = self.df_class[self.df_class['teacher']==i]['status'].unique()
                for s in status:
                    if self.df_teach[self.df_teach['TEACHER']==i][s].values[0] == 0:
                        print(f'Teacher {i} cannot teach in status {s}')
            
