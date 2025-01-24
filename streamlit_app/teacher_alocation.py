from ortools.sat.python import cp_model
import pandas as pd

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

        self.alocacoes = {}
        self.model = cp_model.CpModel()

    def schedule_teachers(self):

        self.create_variables()
        self.add_teacher_constraints()
        self.add_schedule_constraints()
        self.add_online_constraints()
        self.add_modalidades_constraints()
        self.add_grupo_constraints()
        self.add_estagio_constraints()
        self.add_time_constraints()
        self.add_consecutive_group_constraints()
        self.add_objective()
        
        prof_alocados = self.solve()
        
        return prof_alocados

    def create_variables(self):
        # Criação das variáveis de alocação
        
        for i in self.df_teach['TEACHER'].unique():
            for g in self.df_class['nome grupo'].unique():
                self.alocacoes[(i, g)] = self.model.NewBoolVar(f"{i}_converinglesson_{g}")

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

    def add_consecutive_group_constraints(self):
        # Restrição: Não alocar o mesmo professor em grupos consecutivos em unidades diferentes

        for x in self.df_class['dias da semana'].unique():
            for j in self.df_class['nome grupo'].unique():
                if self.df_class.loc[(self.df_class['nome grupo'] == j) & (self.df_class['dias da semana'] == x), 'horario'].empty:
                    continue
                status = self.df_class.loc[(self.df_class['nome grupo'] == j) & (self.df_class['dias da semana'] == x), 'status'].values[0]
                if status == 'PRESENCIAL':
                    horario_da_turma, unidade_da_turma = self.df_class.loc[
                        (self.df_class['nome grupo'] == j) & (self.df_class['dias da semana'] == x),
                        ['horario_tratado', 'unidade']
                    ].values[0]
                    
                    grupos_seguidos = self.df_class.loc[
                        (self.df_class['dias da semana'] == x) & 
                        (self.df_class['horario'] == (horario_da_turma + pd.Timedelta(hours=1)).strftime('%H:%M:%S')) & 
                        (self.df_class['unidade'] != unidade_da_turma) & 
                        (self.df_class['status'] == 'PRESENCIAL'), 
                        'nome grupo' #corrigir esse. Nem toda aulas seguida é 1h depois. pode ser 10,30 50 minutos etc...
                    ].unique()

                    grupos_seguidos = list(grupos_seguidos)
                    grupos_seguidos.append(j)

                    if len(grupos_seguidos) > 1:
                        for i in self.df_teach['TEACHER'].unique():
                            self.model.Add(sum(self.alocacoes[(i, g)] for g in grupos_seguidos) <= 1)

    def add_modalidades_constraints(self):
        # Restrição: Professores que não podem dar aulas em determinadas modalidades

        modality_list = [ 'Espanhol','Kids','CONV - Ing Prep','CONV - Ing Intemed',
                          'CONV - Ing Avançado','CONV - Esp Prep','CONV - Esp Intemed',
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

    def add_estagio_constraints(self):
        # Restrição: Professores que não podem dar aulas em estágios

        estagio_list = self.df_class.loc[self.df_class['stage'].str.contains('ESTAGIO|MBA', na=False)]['stage'].unique()
        for est in estagio_list:
            for i in self.df_teach.loc[self.df_teach[est] == 0, 'TEACHER'].to_list():
                for g in self.df_class.loc[self.df_class['stage'] == est, 'nome grupo'].unique():
                    self.model.Add(self.alocacoes[(i, g)] == 0)

    def add_online_constraints(self):
        # Restrição: Professores não podem dar aulas online

        for i in self.df_teach.loc[(self.df_teach['ONLINE'] == 0), 'TEACHER'].to_list():
            for g in self.df_class.loc[self.df_class['status'] == 'ONLINE']['nome grupo'].unique():
                self.model.Add(self.alocacoes[(i, g)] == 0)
        
        for i in self.df_teach.loc[self.df_teach['PRESENCIAL'] == 0, 'TEACHER'].to_list():
            for g in self.df_class.loc[self.df_class['status']=='PRESENCIAL']['nome grupo'].unique():
                self.model.Add(self.alocacoes[(i, g)] == 0)
    
    def add_time_constraints(self):
        # Restrição: Professores não podem dar aulas em horários que não estão disponíveis

        for g in self.df_class['nome grupo'].unique():
            for i in self.df_teach['TEACHER'].unique():
                time_class = self.df_class.loc[self.df_class['nome grupo'] == g, 'horario'].to_list()
                if self.df_teach.loc[self.df_teach['TEACHER'] == i, time_class].sum(axis=1).values[0] == 0:
                    self.model.Add(self.alocacoes[(i, g)] == 0)

        for i in self.df_teach['TEACHER'].unique():
            for x in self.df_class['dias da semana'].unique():
                turmas_do_dia = self.df_class[self.df_class['dias da semana']==x]['nome grupo'].unique()
                if self.df_teach[self.df_teach['TEACHER']==i][x].values[0] == 0:
                    for g in turmas_do_dia:
                        self.model.Add(self.alocacoes[(i, g)] == 0)

    def add_objective(self):
        total_allocation = sum(self.alocacoes[(i, g)] for i in self.df_teach['TEACHER'].unique() for g in self.df_class['nome grupo'].unique())
        self.model.Maximize(total_allocation)

    def solve(self):
        # Resolver o modelo e alocar os Professores
        solver = cp_model.CpSolver()

        # Tentar buscar todas as combinações possíveis
        solver.parameters.search_branching = cp_model.FIXED_SEARCH
        status = solver.Solve(self.model)   

        prof_alocados = pd.DataFrame(columns=['Professor', 'nome grupo'])

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            for g in self.df_class['nome grupo'].unique():
                for i in self.df_teach['TEACHER'].unique():
                    if solver.Value(self.alocacoes[(i, g)]):
                        aloca = pd.DataFrame({'Professor': [i], 'nome grupo': [g]})
                        prof_alocados = pd.concat([prof_alocados, aloca], ignore_index=True)
        else:
            print("Não foi possível encontrar uma solução ótima.")

        return prof_alocados
    