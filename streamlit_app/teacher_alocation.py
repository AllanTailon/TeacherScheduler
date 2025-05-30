from ortools.sat.python import cp_model
import pandas as pd
import random
import numpy as np

class TeacherScheduler:
    """
    Classe para alocação de professores em grupos de aulas, considerando restrições de horários, 
    tipo de aula (presencial ou online), uso de computador, e competência em idiomas.

    Atributos:
    ----------
    df_class : pd.DataFrame
        DataFrame contendo os dados das aulas, incluindo colunas como 'nome grupo', 'horario', 'dias da semana', 'status', 'unidade', etc.
    df_teach : pd.DataFrame
        DataFrame contendo as informações dos professores, contendo colunas como nome, competência em idiomas, uso de computador, etc.
    alocacoes : dict
        Dicionário onde as chaves são combinações de (professor, grupo) e os valores são variáveis binárias que indicam se o professor foi alocado ao grupo.
    model : cp_model.CpModel
        Instância do modelo CP-SAT da OR-Tools.

    Métodos:
    --------
    schedule_teachers():
        Função principal que coordena a criação de variáveis, aplicação de restrições e a resolução do modelo.
    
    create_variables():
        Cria as variáveis binárias que representam a alocação de professores a grupos.
    
    add_professor_constraints():
        Adiciona a restrição de que cada grupo deve ter apenas um professor alocado.
    
    add_schedule_constraints():
        Adiciona a restrição de que um professor não pode ser alocado a mais de um grupo no mesmo horário.
    
    add_consecutive_group_constraints():
        Adiciona a restrição para evitar que um professor seja alocado a grupos consecutivos com unidades diferentes.
    
    add_online_constraints():
        Adiciona a restrição de quais professores podem dar aulas online.
    
    add_modalidades_constraints():
        Adiciona a restrição de quais modalidades o professor pode dar aulas.
    
    solve():
        Resolve o modelo de otimização e retorna um DataFrame com as alocações de professores para os grupos.

    """

    def __init__(self, df_class, df_teach):
        """
        Inicializa a classe TeacherScheduler.

        Parâmetros:
        -----------
        df_class : pd.DataFrame
            DataFrame contendo os dados das aulas, incluindo informações sobre grupos, horários, dias da semana e status das aulas.
        df_teach : pd.DataFrame
            DataFrame contendo as informações dos professores, incluindo se possuem computador e se falam espanhol.
        """
        self.df_class = df_class
        self.df_teach = df_teach

    def schedule_teachers(self,use_soft_constrait=0,seed=None):
        
        self.create_model()
        self.create_variables()
        self.add_teacher_pre_alocation()
        self.add_teacher_constraints()
        self.add_schedule_constraints()
        self.add_impossible_group_constraints()
        self.add_consecutive_group_constraints()
        self.add_modalidades_constraints()
        self.add_grupo_constraints()
        self.add_estagio_constraints()
        self.add_online_constraints()
        self.add_time_constraints()
        self.add_intensive_constraints()
        self.add_restrictions_constraints()
        self.add_all_class_fill_constraints()
        self.teacher_at_least_1_class_constraints()


        if use_soft_constrait == 0:
            self.add_class_per_teacher_constraints_hard()
            self.add_consecutive_teacher_constraints_soft()
        elif use_soft_constrait == 1:
            self.add_class_per_teacher_constraints_weighted()
            self.add_consecutive_teacher_constraints()
        elif use_soft_constrait == 2:
            self.add_class_per_teacher_constraints_double_weighted()


        prof_alocados = self.solve(seed = seed)
        
        return prof_alocados
    
    def create_model(self):
        # Cria o modelo de alocação
        self.alocacoes = {}
        self.model = cp_model.CpModel()

    def create_variables(self):
        # Criação das variáveis de alocação
        
        for i in self.df_teach['TEACHER'].unique():
            for g in self.df_class['nome grupo'].unique():
                self.alocacoes[(i, g)] = self.model.NewBoolVar(f"{i}_converinglesson_{g}")

    def add_teacher_pre_alocation(self):
        # Restrição: Professores que já estão alocados

        for i in self.df_teach['TEACHER'].unique():
            for g in self.df_class.loc[self.df_class['teacher'] == i, 'nome grupo'].unique():
                self.model.Add(self.alocacoes[(i, g)] == 1)

    def add_teacher_constraints(self):
        # Restrição: Apenas um professor por grupo

        for g in self.df_class['nome grupo'].unique():
            self.model.Add(sum(self.alocacoes[(i, g)] for i in self.df_teach['TEACHER'].unique()) <= 1)

    def add_schedule_constraints(self):
        # Restrição: Professores não podem ser alocados em mais de um grupo no mesmo horário

        for h in self.df_class['horario'].unique():
            for d in self.df_class['dias da semana'].unique():
                grupos_no_mesmo_horario = self.df_class.loc[
                    (self.df_class['horario'] == h) & 
                    (self.df_class['dias da semana'] == d)
                ]['nome grupo'].unique()
                
                for i in self.df_teach['TEACHER'].unique():
                    self.model.Add(sum(self.alocacoes[(i, g)] for g in grupos_no_mesmo_horario) <= 1)

    def add_impossible_group_constraints(self):
        # Restrição: Não alocar o mesmo professor em grupos com intervalo menor que 50 minutos

        for x in self.df_class['dias da semana'].unique():
            for j in self.df_class['nome grupo'].unique():
                if self.df_class.loc[(self.df_class['nome grupo'] == j) & (self.df_class['dias da semana'] == x), 'horario'].empty:
                    continue
                horario_da_turma = self.df_class.loc[
                    (self.df_class['nome grupo'] == j) & (self.df_class['dias da semana'] == x),
                    'horario_tratado'
                ].values[0]

                list_minutes = [10,20,30,40,50]

                horarios_impossiveis = []

                for minutes in list_minutes:
                    horarios_impossiveis.append((horario_da_turma + pd.Timedelta(minutes=minutes)).strftime('%H:%M:%S'))

                grupos_impossivel = self.df_class.loc[
                    (self.df_class['dias da semana'] == x) &
                    (self.df_class['horario'].isin(horarios_impossiveis)),
                    'nome grupo'
                ].unique()

                grupos_impossivel = list(grupos_impossivel)
                grupos_impossivel.append(j)

                if len(grupos_impossivel) > 1:
                    for i in self.df_teach['TEACHER'].unique():
                        self.model.Add(sum(self.alocacoes[(i, g)] for g in grupos_impossivel) <= 1)

    def add_consecutive_group_constraints(self):
        # Restrição: Não alocar o mesmo professor em grupos consecutivos em unidades diferentes
        pares_total = set()
        for j in self.df_class.loc[self.df_class['status'] == 'PRESENCIAL', 'nome grupo'].unique():
            turmas_turnos_diferentes = set()
            for x in self.df_class.loc[self.df_class['status'] == 'PRESENCIAL', 'dias da semana'].unique():
                
                filtro = (self.df_class['nome grupo'] == j) & (self.df_class['dias da semana'] == x)
                
                if self.df_class.loc[filtro, 'unidade'].empty:
                    continue
                
                unidade, horario = self.df_class.loc[filtro, ['unidade', 'horario_tratado']].values[0]
                
                if horario.hour <= 12:
                    turmas_turnos_oposto = self.df_class.loc[
                        (self.df_class['dias da semana'] == x) &
                        (self.df_class['horario_tratado'] <= pd.to_datetime('1900-01-01 12:00:00')) &
                        (self.df_class['status'] == 'PRESENCIAL') &
                        (self.df_class['unidade'] != unidade),
                        'nome grupo'
                    ].to_list()
                elif horario.hour > 12:
                    turmas_turnos_oposto = self.df_class.loc[
                        (self.df_class['dias da semana'] == x) &
                        (self.df_class['horario_tratado'] > pd.to_datetime('1900-01-01 12:00:00')) &
                        (self.df_class['status'] == 'PRESENCIAL') &
                        (self.df_class['unidade'] != unidade),
                        'nome grupo'
                    ].to_list()
                turmas_turnos_diferentes.update(turmas_turnos_oposto)
            pares_total.update(tuple(sorted([j, t])) for t in turmas_turnos_diferentes)

        for i in self.df_teach['TEACHER'].unique():
            for t in pares_total:
                self.model.Add(self.alocacoes[(i, t[0])] + self.alocacoes[(i, t[1])] <= 1)


    def add_consecutive_teacher_constraints(self):
        # Restrição: Não alocar o mesmo professor em grupos consecutivos

        for g in self.df_class[((self.df_class['teacher']=='-')|(self.df_class['teacher'].isnull()))]['nome grupo'].unique():
            last_teacher = self.df_class.loc[self.df_class['nome grupo'] == g, 'ultimo_professor'].dropna().unique()[0]

            if last_teacher in self.df_teach['TEACHER'].values and last_teacher != 'nan':
                self.model.Add(self.alocacoes[(last_teacher, g)] == 0)

    def add_consecutive_teacher_constraints_soft(self, penalty_weight=1):
        """
        Adiciona restrições suaves para evitar alocar o mesmo professor do grupo anterior.
        Penaliza a repetição de professor com uma variável auxiliar no objetivo.
        """
        penalidades = []

        grupos_sem_professor = self.df_class[
            (self.df_class['teacher'] == '-') | (self.df_class['teacher'].isnull())
        ]['nome grupo'].unique()

        for g in grupos_sem_professor:
            grupo_info = self.df_class[self.df_class['nome grupo'] == g]

            if grupo_info['ultimo_professor'].notnull().any():
                last_teacher = grupo_info['ultimo_professor'].dropna().unique()[0]

                if last_teacher in self.df_teach['TEACHER'].values:
                    # Criar variável binária que indica se o último professor foi repetido
                    var_penalidade = self.model.NewBoolVar(f'penalidade_repeticao_{last_teacher}_{g}')

                    # Conectar essa variável à alocação do professor
                    self.model.Add(self.alocacoes[(last_teacher, g)] == 1).OnlyEnforceIf(var_penalidade)
                    self.model.Add(self.alocacoes[(last_teacher, g)] == 0).OnlyEnforceIf(var_penalidade.Not())

                    # Adicionar penalidade ao objetivo
                    penalidades.append(var_penalidade * penalty_weight)

        # Minimizar a soma das penalidades
        self.model.Minimize(sum(penalidades))

    def add_modalidades_constraints(self):
        # Restrição: Professores que não podem dar aulas em determinadas modalidades

        modality_list = [ 'Espanhol','Kids','CONV - Ing Prep','CONV - Ing Intermed',
                          'CONV - Ing Avançado','CONV - Esp Prep','CONV - Esp Intermed',
                          'CONV - Esp Avançado','MBA']
        for mod in modality_list:
            for i in self.df_teach.loc[self.df_teach[mod] == 0, 'TEACHER'].to_list():
                for g in self.df_class.loc[self.df_class['modalidade'] == mod, 'nome grupo'].unique():
                    self.model.Add(self.alocacoes[(i, g)] == 0)

    def add_grupo_constraints(self):
        # Restrição: Professores que não podem dar aulas em determinados grupos

        grupo_list = ['Grupo', 'VIP', 'In Company', 'VIP - In Company']
        for grp in grupo_list:
            for i in self.df_teach.loc[self.df_teach[grp] == 0, 'TEACHER'].to_list():
                for g in self.df_class.loc[self.df_class['grupo'] == grp, 'nome grupo'].unique():
                    self.model.Add(self.alocacoes[(i, g)] == 0)

    def add_class_per_teacher_constraints_hard(self):
        # Restrição: Professores que não podem dar aulas em mais de 3 grupos ou menos de 3 aulas baseado na media (retrição alta)
        for i in self.df_teach['TEACHER'].unique():
            media = self.df_teach.loc[self.df_teach['TEACHER'] == i, 'MEDIA'].values[0]
            max_aulas_professor = (media).astype(int)
            min_aulas_professor = (media - 4).astype(int)

            self.model.Add(
                sum(self.alocacoes[(i, g)] * self.df_class.loc[self.df_class['nome grupo'] == g, 'n aulas'].values[0].astype(int)
                    for g in self.df_class['nome grupo'].unique()) <= max_aulas_professor
            )
            self.model.Add(
                sum(self.alocacoes[(i, g)] * self.df_class.loc[self.df_class['nome grupo'] == g, 'n aulas'].values[0].astype(int)
                    for g in self.df_class['nome grupo'].unique()) >= min_aulas_professor
            )

    def add_class_per_teacher_constraints_double_weighted(self, weight_media=5, weight_repeticao=2):
        teachers = self.df_teach['TEACHER'].unique()
        grupos = self.df_class['nome grupo'].unique()

        # Variáveis auxiliares: total de aulas alocadas por professor
        aulas_alocadas = {}
        desvios = []

        for i in teachers:
            media = self.df_teach.loc[self.df_teach['TEACHER'] == i, 'MEDIA'].values[0]
            max_aulas_professor = int(media)

            # Criando variável auxiliar para contar total de aulas alocadas ao professor i
            aulas_alocadas[i] = self.model.NewIntVar(0, max_aulas_professor, f"aulas_alocadas_{i}")
            desvio = self.model.NewIntVar(0, max_aulas_professor, f"desvio_{i}")

            self.model.Add(
                aulas_alocadas[i] == sum(
                    self.alocacoes[(i, g)] * int(self.df_class.loc[self.df_class['nome grupo'] == g, 'n aulas'].values[0])
                    for g in grupos
                )
            )

            self.model.Add(desvio >= media - aulas_alocadas[i])
            self.model.Add(aulas_alocadas[i] <= max_aulas_professor)

            # Peso para desvio da média
            desvios.append(desvio * int(media / 8) * weight_media)

        # -----------------------------
        # Penalidade por repetição de professor
        penalidades = []

        grupos_sem_professor = self.df_class[
            (self.df_class['teacher'] == '-') | (self.df_class['teacher'].isnull())
        ]['nome grupo'].unique()

        for g in grupos_sem_professor:
            grupo_info = self.df_class[self.df_class['nome grupo'] == g]

            if grupo_info['ultimo_professor'].notnull().any():
                last_teacher = grupo_info['ultimo_professor'].dropna().unique()[0]

                if last_teacher in self.df_teach['TEACHER'].values:
                    var_penalidade = self.model.NewBoolVar(f'penalidade_repeticao_{last_teacher}_{g}')

                    self.model.Add(self.alocacoes[(last_teacher, g)] == 1).OnlyEnforceIf(var_penalidade)
                    self.model.Add(self.alocacoes[(last_teacher, g)] == 0).OnlyEnforceIf(var_penalidade.Not())

                    penalidades.append(var_penalidade * weight_repeticao)

        # -----------------------------
        # Minimiza a soma ponderada de desvios + penalidades por repetição
        self.model.Minimize(sum(desvios) + sum(penalidades))

    def add_class_per_teacher_constraints_weighted(self):
        teachers = self.df_teach['TEACHER'].unique()
        grupos = self.df_class['nome grupo'].unique()

        # Variáveis auxiliares: total de aulas alocadas por professor
        aulas_alocadas = {}
        pesos_desvios = {}

        for i in teachers:
            media = self.df_teach.loc[self.df_teach['TEACHER'] == i, 'MEDIA'].values[0]
            max_aulas_professor = int(media)

            # Criando variável auxiliar para contar total de aulas alocadas ao professor i
            aulas_alocadas[i] = self.model.NewIntVar(0, max_aulas_professor, f"aulas_alocadas_{i}")
            desvio = self.model.NewIntVar(0, max_aulas_professor, f"desvio_{i}")

            # Soma de aulas atribuídas ao professor i
            self.model.Add(
                aulas_alocadas[i] == sum(
                    self.alocacoes[(i, g)] * int(self.df_class.loc[self.df_class['nome grupo'] == g, 'n aulas'].values[0])
                    for g in grupos
                )
            )
            self.model.Add(desvio >= media - aulas_alocadas[i])

            # Restrição de máximo
            self.model.Add(aulas_alocadas[i] <= max_aulas_professor)

            pesos_desvios[i] = desvio


        # Agora maximizamos a soma ponderada de aulas alocadas com peso baseado na média
        self.model.Minimize(
            sum(
                pesos_desvios[i] * int(self.df_teach.loc[self.df_teach['TEACHER'] == i, 'MEDIA'].values[0]/8)
                for i in teachers
            )
        )

    def add_estagio_constraints(self):
        # Restrição: Professores que não podem dar aulas em estágios

        estagio_list = self.df_class.loc[self.df_class['stage'].str.contains('ESTAGIO', na=False)]['stage'].unique()
        for est in estagio_list:
            for i in self.df_teach.loc[self.df_teach[est] == 0, 'TEACHER'].to_list():
                for g in self.df_class.loc[((self.df_class['stage'] == est)&(self.df_class['modalidade']!='Espanhol')), 'nome grupo'].unique():
                    self.model.Add(self.alocacoes[(i, g)] == 0)

    def add_online_constraints(self):
        # Restrição: Professores não podem dar aulas online
        for sts in ['ONLINE', 'PRESENCIAL']:
            for i in self.df_teach.loc[(self.df_teach[sts] == 0), 'TEACHER'].to_list():
                for g in self.df_class.loc[self.df_class['status'] == sts]['nome grupo'].unique():
                    self.model.Add(self.alocacoes[(i, g)] == 0)
    
    def add_time_constraints(self):
        # Restrição: Professores não podem dar aulas em horários que não estão disponíveis

        for g in self.df_class[self.df_class['dias da semana']!='SÁBADO']['nome grupo'].unique():
            for i in self.df_teach['TEACHER'].unique():
                time_class = self.df_class.loc[self.df_class['nome grupo'] == g, 'horario'].to_list()
                if self.df_teach.loc[self.df_teach['TEACHER'] == i, time_class].sum(axis=1).values[0] == 0:
                    self.model.Add(self.alocacoes[(i, g)] == 0)

            for i in self.df_teach['TEACHER'].unique():
                for x in self.df_class['dias da semana'].unique():
                    turmas_do_dia = self.df_class[self.df_class['dias da semana'] == x]['nome grupo'].unique()
                    disponibilidade = self.df_teach[self.df_teach['TEACHER'] == i][x].values[0]

                    if disponibilidade == 0:
                        # Se o professor não pode dar aula no dia, todas as alocações devem ser 0
                        for g in turmas_do_dia:
                            self.model.Add(self.alocacoes[(i, g)] == 0)

    def add_intensive_constraints(self):
        # Restrição: Professores que não podem dar aulas em intensivos

        for i in self.df_teach.loc[self.df_teach['INTENSIVÃO'] == 0, 'TEACHER'].to_list():
            for g in self.df_class.loc[self.df_class['n aulas'] >= 10, 'nome grupo'].unique():
                self.model.Add(self.alocacoes[(i, g)] == 0)
    
    def add_restrictions_constraints(self):
        # Restrição: Professores que não podem dar aulas em determinados grupos

        for g in self.df_class[self.df_class['restricoes_professor'].notnull()]['nome grupo'].unique():
            restricoes_prof = self.df_class[self.df_class['nome grupo']==g]['restricoes_professor'].unique()[0].split(',')
            for i in restricoes_prof:
                if i in self.df_teach['TEACHER'].unique():
                    self.model.Add(self.alocacoes[(i, g)] == 0)

    
    def add_all_class_fill_constraints(self):
        # Restrição: Garantir que todas as aulas sejam preenchidas
        for g in self.df_class['nome grupo'].unique():
            self.model.Add(sum(self.alocacoes[(i, g)] for i in self.df_teach['TEACHER'].unique()) == 1)
    
    def teacher_at_least_1_class_constraints(self):
        # Restrição: Garantir que todas as aulas sejam preenchidas
        for i in self.df_teach['TEACHER'].unique():
            self.model.Add(sum(self.alocacoes[(i, g)] for g in self.df_class['nome grupo'].unique()) >= 1)

    def solve(self,seed):
        # Resolver o modelo e alocar os Professores
        solver = cp_model.CpSolver()

        # Tentar buscar todas as combinações possíveis
        if seed == None :
            solver.parameters.random_seed = random.randint(1, 10000)
        else:
            solver.parameters.random_seed = seed
        print(solver.parameters.random_seed)
        # Permitir busca aleatória
        solver.parameters.search_branching = cp_model.AUTOMATIC_SEARCH  # Pode testar cp_model.RANDOM_SEARCH também
        solver.parameters.max_time_in_seconds = 60
        solver.parameters.enumerate_all_solutions = False
        status = solver.Solve(self.model)   
        

        prof_alocados = pd.DataFrame(columns=['professores_alocados', 'nome grupo'])

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            print(status)
            for g in self.df_class['nome grupo'].unique():
                for i in self.df_teach['TEACHER'].unique():
                    if solver.Value(self.alocacoes[(i, g)]):
                        aloca = pd.DataFrame({'professores_alocados': [i], 'nome grupo': [g]})
                        prof_alocados = pd.concat([prof_alocados, aloca], ignore_index=True)
        else:
            print("Não foi possível encontrar uma solução ótima.")

        return prof_alocados
    