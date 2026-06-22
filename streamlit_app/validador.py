import pandas as pd
import numpy as np
import streamlit as st

class validador:

    def __init__(self, df_class, df_teach):

        self.df_class = df_class
        self.df_teach = df_teach
        self.teacher_alocated = self.df_class[
            (self.df_class['teacher'].notnull()) &
            (self.df_class['teacher'].astype(str).str.strip() != '-') &
            (self.df_class['teacher'].astype(str).str.strip().str.lower() != 'nan')
        ]['teacher'].unique()

    def check_problem(self):

        self.check_existent_teacher()
        self.check_existent_hour()
        self.check_duplicated_class()
        self.check_allowed_time()
        self.check_multiple_classes()
        self.check_impossible_time()
        self.check_modality_group()
        self.check_teach_status()
        self.check_days_of_week()
        self.check_stage()
        self.check_sequence_classes()
        self.validator_min_classes()
        self.check_restrictions_teacher()
        self.check_teacher_class_type()
        self.check_unidade()

    def check_existent_teacher(self):
        """
        Check if there are teachers in the class that are not in the teacher table
        """
        teachers = self.df_teach['TEACHER'].unique()
        diff = set(self.teacher_alocated) - set(teachers)
        if diff:
            message = f'Professor nao encontrado na tabela de professores: {diff}'
            st.write(message)

    def check_existent_hour(self):
        """
        Check if there are hours in the class that are not in the teacher table
        """
        horas_aula = self.df_class['horario'].unique()
        colunas = self.df_teach.columns
        diff = set(horas_aula) - set(colunas)
        turmas_diff = self.df_class[self.df_class['horario'].isin(diff)]['nome grupo'].unique()
        if diff:
            message = f'Horário nao encontrado na tabela de professores: {diff} para as turmas: {turmas_diff}'
            st.write(message)
    
    def check_duplicated_class(self):
        """
        Check if there are duplicated classes
        """
        turmas_unicas = self.df_class.drop_duplicates(subset=['nome grupo','unidade'])

        duplicado_1 = turmas_unicas[turmas_unicas.duplicated(subset=['nome grupo'])]['nome grupo'].to_list()
        duplicado_2 = self.df_class[self.df_class.duplicated(subset=['nome grupo','horario','dias da semana'])]['nome grupo'].to_list()
        duplicado = set(duplicado_1 + duplicado_2)
        if duplicado:
            message = f'Turmas duplicadas: {duplicado}'
            st.write(message)
            

    def check_allowed_time(self):
        """
        Check if the hours in the class are possible
        """
        horarios_nao_permitido = {}
        dia_da_semana_nao_permitido = {}

        for professor in self.teacher_alocated:
            horarios = self.df_class[self.df_class['teacher']==professor]['horario'].unique()
            dia_semana = self.df_class[self.df_class['teacher']==professor]['dias da semana'].unique()

            if professor not in self.df_teach['TEACHER'].values:
                continue

            horarios_existentes = [h for h in horarios if h in self.df_teach.columns]
            dias_existentes = [d for d in dia_semana if d in self.df_teach.columns]

            prof_horarios = self.df_teach[self.df_teach['TEACHER']==professor][horarios_existentes]
            prof_diasemana = self.df_teach[self.df_teach['TEACHER']==professor][dias_existentes]

            erros_horario = prof_horarios.columns[(prof_horarios == 0).any()].to_list()
            erros_diasemana = prof_diasemana.columns[(prof_diasemana == 0).any()].to_list()

            if erros_horario:
                horarios_nao_permitido[professor] = erros_horario
            if erros_diasemana:
                dia_da_semana_nao_permitido[professor] = erros_diasemana

        if horarios_nao_permitido:
            message1 = f'Horários não permitidos para os professores: {horarios_nao_permitido}'
            st.write(message1)
        if dia_da_semana_nao_permitido:
            message2 = f'Dia da semana não permitidos para os professores: {dia_da_semana_nao_permitido}'
            st.write(message2)
    
    def check_impossible_time(self):
        """
        Check if pre-allocated classes have start times within 50 minutes.
        """
        for professor in self.teacher_alocated:
            for diasemana in self.df_class[self.df_class['teacher']==professor]['dias da semana'].unique():
                aulas_professor = self.df_class[
                    (self.df_class['teacher'] == professor) &
                    (self.df_class['dias da semana'] == diasemana)
                ][['nome grupo', 'horario']].drop_duplicates().copy()

                if len(aulas_professor) < 2:
                    continue
                
                aulas_professor['horario_tratado'] = pd.to_datetime(aulas_professor['horario'], format="%H:%M:%S")
                aulas_professor = aulas_professor.sort_values('horario_tratado').reset_index(drop=True)

                conflitos = []
                for idx, aula_1 in aulas_professor.iterrows():
                    for idx_2 in range(idx + 1, len(aulas_professor)):
                        aula_2 = aulas_professor.iloc[idx_2]

                        if aula_1['nome grupo'] == aula_2['nome grupo']:
                            continue

                        diff = aula_2['horario_tratado'] - aula_1['horario_tratado']
                        if diff > pd.Timedelta(minutes=50):
                            break

                        if diff > pd.Timedelta(minutes=0):
                            conflitos.append((aula_1['nome grupo'], aula_2['nome grupo']))

                if conflitos:
                    message = (
                        f"Professor {professor} tem turmas com intervalo de até 50 minutos "
                        f"no dia da semana {diasemana}: {conflitos}"
                    )
                    st.write(message)

    def check_multiple_classes(self):
        """
        Check if there are multiple classes in the same hour
        """
        for professor in self.teacher_alocated:
            for diasemana in self.df_class[self.df_class['teacher']==professor]['dias da semana'].unique():
                for horario in self.df_class[self.df_class['teacher']==professor]['horario'].unique():
                    turmas = self.df_class[(self.df_class['teacher']==professor)&(self.df_class['dias da semana']==diasemana)&(self.df_class['horario']==horario)]['nome grupo'].unique()
                    if len(turmas)>1:
                        message = f'Professor {professor} possui turmas no mesmo horario: {turmas}'
                        st.write(message)
    
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
            message1 = f'Modalidade nao encontrada na tabela de professores: {diff_mod} para a seguintes turmas: {aulas_mod}'
            st.write(message1)
        if diff_grupo:
            message2 = f'Grupos nao encontrado na tabela de professores: {diff_grupo} para a seguintes turmas: {aulas_grupo}'
            st.write(message2)
        
        for i in self.teacher_alocated:
            if i in self.df_teach['TEACHER'].unique():
                mod = self.df_class[self.df_class['teacher']==i]['modalidade'].unique()
                for m in mod:
                    if m != 'Inglês' and m in self.df_teach.columns:
                        if self.df_teach[self.df_teach['TEACHER']==i][m].values[0] == 0:
                            message = f'Professor {i} nao pode dar aula na modalidade: {m}'
                            st.write(message)

    def check_teach_status(self):
        """
        Check if the teacher is active
        """
        for i in self.teacher_alocated:
            if i in self.df_teach['TEACHER'].unique():
                status = self.df_class[self.df_class['teacher']==i]['status'].unique()
                for s in status:
                    if s in self.df_teach.columns and self.df_teach[self.df_teach['TEACHER']==i][s].values[0] == 0:
                        message= f'Professor {i} nao pode dar aula no status: {s}'
                        st.write(message)
    
    def check_days_of_week(self):
        """
        Check if the days of the week are correct
        """
        dias_da_semana = ['SEGUNDA', 'TERÇA', 'QUARTA', 'QUINTA', 'SEXTA', 'SÁBADO']
        diff = set(self.df_class['dias da semana'].unique()) - set(dias_da_semana)
        if diff:
            classes = self.df_class[self.df_class['dias da semana'].isin(diff)]['nome grupo'].unique()
            message = f'Dia da semana nao está certo :{diff} para a turma : {classes}'
            st.write(message)
            
    def check_stage(self):
        estagio_list = self.df_class.loc[~(self.df_class['stage'].str.contains('ESTAGIO|MBA|CONV', na=False))]['stage'].unique()
        turmas_list = self.df_class.loc[~(self.df_class['stage'].str.contains('ESTAGIO|MBA|CONV', na=False))]['nome grupo'].unique()
        if len(estagio_list) > 0:
            message = f' ESTAGIO com problema: {estagio_list} para os estagios: {turmas_list}'
            st.write(message)

        for i in self.teacher_alocated:
            stage = self.df_class.loc[((self.df_class['stage'].str.contains('ESTAGIO', na=False))&(self.df_class['teacher']==i)&(self.df_class['modalidade']!='Espanhol'))]['stage'].unique()
            if i in self.df_teach['TEACHER'].values:
                for s in stage:
                    if self.df_teach[self.df_teach['TEACHER']==i][s].values[0] == 0:
                        message = f'Professor {i} nao pode dar aula no estagio: {s}'
                        st.write(message)
    
    def check_sequence_classes(self): #editar essa função para o novo tipo de codigo
        """
        Verifica se as aulas seguidas são de uma mesma unidade, separando em dois períodos:
        -> Antes do meio-dia
        -> Depois do meio-dia
        """
        meio_dia = pd.to_datetime('12:00').time()

        for professor in self.teacher_alocated:
            for diasemana in self.df_class[self.df_class['teacher'] == professor]['dias da semana'].unique():
                # Filtra as aulas do professor naquele dia (presenciais)
                df_prof = self.df_class[
                    (self.df_class['teacher'] == professor) &
                    (self.df_class['dias da semana'] == diasemana) &
                    (self.df_class['status'] == 'PRESENCIAL')
                ].sort_values(by='horario_tratado')  # Ordena pelo horário

                # Se houver menos de 2 aulas, não há comparação a fazer
                if len(df_prof) < 2:
                    continue

                df_manha = df_prof[df_prof['horario_tratado'].dt.time <= meio_dia]
                df_tarde = df_prof[df_prof['horario_tratado'].dt.time > meio_dia]

                if len(df_tarde) < 2 and len(df_manha) < 2:
                    continue

                # Verifica se tem mais de uma unidade no período
                unidades_manha = df_manha['unidade'].unique()
                unidades_tarde = df_tarde['unidade'].unique()
                if len(unidades_manha) > 1:
                    turmas = df_manha['nome grupo'].tolist()
                    message = (
                        f"Conflito Manhã: Professor {professor} nos dias {diasemana}. "
                        f"tem aulas em unidades diferentes {unidades_manha.tolist()}. "
                        f"Turmas: {turmas}"
                        )
                    st.write(message)

                elif len(unidades_tarde) > 1:
                    turmas = df_tarde['nome grupo'].tolist()
                    message = (
                        f"Conflito Manhã: Professor {professor} nos dias {diasemana}. "
                        f"tem aulas em unidades diferentes {unidades_tarde.tolist()}. "
                        f"Turmas: {turmas}"
                        )
                    st.write(message)


    def validator_min_classes(self):
        """
        Verifica se as turmas já pré-alocadas ultrapassam a MEDIA do professor.
        """
        
        if 'TEACHER' not in self.df_teach.columns or 'MEDIA' not in self.df_teach.columns:
            raise ValueError("DataFrame de professores precisa das colunas 'TEACHER' e 'MEDIA'")
        
        if 'teacher' not in self.df_class.columns or 'n aulas' not in self.df_class.columns:
            raise ValueError("DataFrame de aulas precisa das colunas 'teacher' e 'n aulas'")
        
        aulas_prealocadas = self.df_class[
            (self.df_class['teacher'].notnull()) &
            (self.df_class['teacher'].astype(str).str.strip() != '-') &
            (self.df_class['teacher'].astype(str).str.strip().str.lower() != 'nan')
        ].drop_duplicates(subset=['teacher', 'nome grupo'])
        carga_professores = aulas_prealocadas.groupby('teacher')['n aulas'].sum()
        
        for _, professor_info in self.df_teach.iterrows():
            nome = professor_info['TEACHER']
            media = professor_info['MEDIA']
            maximo = (media)  # Garante mínimo zero
            
            aulas_alocadas = carga_professores.get(nome, 0)
            
            if aulas_alocadas > maximo:
                excesso = aulas_alocadas - maximo
                
                st.write(
                    f"PROFESSOR PRÉ-ALOCADO ACIMA DA MÉDIA: {nome} | "
                    f"Aulas pré-alocadas: {aulas_alocadas} | "
                    f"Máximo: {maximo} | "
                    f"Excesso: {excesso} aula(s)"
                )

    def check_restrictions_teacher(self):
        """
        Verifica se professor pré-alocado aparece na coluna restricoes_professor da turma.
        """
        df_restricoes = self.df_class[
            (self.df_class['teacher'].notnull()) &
            (self.df_class['teacher'].astype(str).str.strip() != '-') &
            (self.df_class['restricoes_professor'].notnull())
        ]

        for _, aula in df_restricoes.iterrows():
            professor = aula['teacher']
            restricoes = [
                item.strip()
                for item in str(aula['restricoes_professor']).split(',')
                if item.strip()
            ]
            if professor in restricoes:
                st.write(
                    f"Professor {professor} está pré-alocado na turma "
                    f"{aula['nome grupo']}, mas aparece em restricoes_professor."
                )
    
    def check_unidade(self):
        """
        Verifica se as unidades estão corretas
        """
        for i in self.teacher_alocated:
            if i in self.df_teach['TEACHER'].unique():
                unidade = self.df_class[(self.df_class['teacher']==i)&(self.df_class['status']=='PRESENCIAL')]['unidade'].unique()
                for uni in unidade:
                    if self.df_teach[self.df_teach['TEACHER']==i][uni.upper()].values[0] == 0:
                        message= f'Professor {i} nao pode dar aula na unidade: {uni}'
                        st.write(message)
    
    def check_teacher_class_type(self):
        for i in self.teacher_alocated:
            if i in self.df_teach['TEACHER'].unique():
                class_type = self.df_class[self.df_class['teacher']==i]['grupo'].unique()
                for ct in class_type:
                    if self.df_teach[self.df_teach['TEACHER']==i][ct].values[0] == 0:
                        message= f'Professor {i} nao pode dar aula no tipo de aula: {ct}'
                        st.write(message)