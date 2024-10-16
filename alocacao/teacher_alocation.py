from ortools.sat.python import cp_model
import pandas as pd

class TeacherScheduler:
    """
    Classe para alocação de professores em grupos de aulas, considerando restrições de horários, 
    tipo de aula (presencial ou online), uso de computador, e competência em idiomas.

    Atributos:
    ----------
    df_class : pd.DataFrame
        DataFrame contendo os dados das aulas, incluindo colunas como 'Grupo', 'Horário', 'Dias da Semana', 'STATUS', 'Unidade', etc.
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
        Adiciona a restrição de que professores sem computador não podem dar aulas online.
    
    add_language_constraints():
        Adiciona a restrição de que professores que não falam espanhol não podem dar aulas de espanhol.
    
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
        self.add_professor_constraints()
        self.add_schedule_constraints()
        self.add_consecutive_group_constraints()
        self.add_online_constraints()
        self.add_language_constraints()
        
        prof_alocados = self.solve()
        
        return prof_alocados

    def create_variables(self):
        # Criação das variáveis de alocação
        for i in self.df_teach['professor'].unique():
            for g in self.df_class['Grupo'].unique():
                self.alocacoes[(i, g)] = self.model.NewBoolVar(f"{i}_converinglesson_{g}")

    def add_professor_constraints(self):
        # Restrição: Apenas um professor por grupo
        for g in self.df_class['Grupo'].unique():
            self.model.Add(sum(self.alocacoes[(i, g)] for i in self.df_teach['professor'].unique()) == 1)

    def add_schedule_constraints(self):
        # Restrição: Professores não podem ser alocados em mais de um grupo no mesmo horário

        for h in self.df_class['Horário'].unique():
            for d in self.df_class['Dias da Semana'].unique():
                grupos_no_mesmo_horario = self.df_class.loc[
                    (self.df_class['Horário'] == h) & 
                    (self.df_class['Dias da Semana'] == d)
                ]['Grupo'].unique()
                
                for i in self.df_teach['professor'].unique():
                    self.model.Add(sum(self.alocacoes[(i, g)] for g in grupos_no_mesmo_horario) <= 1)

    def add_consecutive_group_constraints(self):
        # Restrição: Não alocar o mesmo professor em grupos consecutivos em unidades diferentes
        for x in self.df_class['Dias da Semana'].unique():
            for j in self.df_class['Grupo'].unique():
                if self.df_class.loc[(self.df_class['Grupo'] == j) & (self.df_class['Dias da Semana'] == x), 'Horário'].empty:
                    continue
                status = self.df_class.loc[(self.df_class['Grupo'] == j) & (self.df_class['Dias da Semana'] == x), 'STATUS'].values[0]
                if status == 'PRESENCIAL':
                    horario_da_turma, unidade_da_turma = self.df_class.loc[
                        (self.df_class['Grupo'] == j) & (self.df_class['Dias da Semana'] == x),
                        ['horario_tratado', 'Unidade']
                    ].values[0]
                    
                    grupos_seguidos = self.df_class.loc[
                        (self.df_class['Dias da Semana'] == x) & 
                        (self.df_class['Horário'] == (horario_da_turma + pd.Timedelta(hours=1)).strftime('%H:%M:%S')) & 
                        (self.df_class['Unidade'] != unidade_da_turma) & 
                        (self.df_class['STATUS'] == 'PRESENCIAL'), 
                        'Grupo'
                    ].unique()

                    grupos_seguidos = list(grupos_seguidos)
                    grupos_seguidos.append(j)

                    if len(grupos_seguidos) > 1:
                        for i in self.df_teach['professor'].unique():
                            self.model.Add(sum(self.alocacoes[(i, g)] for g in grupos_seguidos) <= 1)

    def add_online_constraints(self):
        # Restrição: Professores sem computador não podem dar aulas online

        for i in self.df_teach.loc[self.df_teach['tem_pc'] == 0, 'professor'].to_list():
            for g in self.df_class.loc[self.df_class['STATUS'] == 'ONLINE']['Grupo'].unique():
                self.model.Add(self.alocacoes[(i, g)] == 0)

    def add_language_constraints(self):
        # Restrição: Professores que não falam espanhol não podem dar aulas de espanhol

        for i in self.df_teach.loc[self.df_teach['fala_espanhol'] == 0, 'professor'].to_list():
            for g in self.df_class.loc[self.df_class['MOD'].str.contains('Espanhol', na=False)]['Grupo'].unique():
                self.model.Add(self.alocacoes[(i, g)] == 0)

    def solve(self):
        # Resolver o modelo e alocar os professores
        solver = cp_model.CpSolver()
        status = solver.Solve(self.model)

        prof_alocados = pd.DataFrame(columns=['Professor', 'Grupo'])

        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            for g in self.df_class['Grupo'].unique():
                for i in self.df_teach['professor'].unique():
                    if solver.Value(self.alocacoes[(i, g)]):
                        aloca = pd.DataFrame({'Professor': [i], 'Grupo': [g]})
                        prof_alocados = pd.concat([prof_alocados, aloca], ignore_index=True)

        return prof_alocados


