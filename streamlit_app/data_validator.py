import pandas as pd

class DataValidator:
    def __init__(self, df):
        self.df = df
        self.errors_report = {}
    
    def add_error(self, col_name, error_type, error_rows):
        """Adiciona erros ao relatório"""
        if col_name not in self.errors_report:
            self.errors_report[col_name] = []
        
        if not isinstance(error_rows, pd.DataFrame):
            error_rows = self.df.loc[error_rows]
        
        self.errors_report[col_name].append({
            'tipo': error_type,
            'linhas': error_rows,
            'quantidade': len(error_rows)
        })
    
    def validate_nome_grupo(self):
        if 'nome grupo' in self.df.columns:
            mask = (
                self.df['nome grupo'].isna() | 
                self.df['nome grupo'].apply(lambda x: str(x).strip() == "") | 
                self.df['nome grupo'].apply(lambda x: isinstance(x, (int, float)))
            )
            if mask.any():
                self.add_error('nome grupo', 'Valores inválidos', mask)
        return self
    
    def validate_horario(self):
        if 'horario' in self.df.columns:
            mask = self.df['horario'].apply(lambda x: isinstance(x, str))
            if mask.any():
                self.add_error('horario', 'Valores em formato de texto', mask)
        return self
    
    def validate_unidade(self):
        if 'unidade' in self.df.columns:
            VALORES_PERMITIDOS = {"satélite", "jardim", "vicentina"}
            mask = self.df['unidade'].apply(
                lambda x: (
                    pd.isna(x) or
                    str(x).strip() == "" or
                    isinstance(x, (int, float)) or
                    str(x).strip().lower() not in VALORES_PERMITIDOS
                )
            )
            if mask.any():
                self.add_error('unidade', 'Valores inválidos', mask)
        return self
    
    def validate_dias_semana(self):
        if 'dias da semana' in self.df.columns:
            mask = (
                self.df['dias da semana'].isna() | 
                self.df['dias da semana'].apply(lambda x: str(x).strip() == "") | 
                self.df['dias da semana'].apply(lambda x: isinstance(x, (int, float)))
            )
            if mask.any():
                self.add_error('dias da semana', 'Valores inválidos', mask)
        return self
    
    def validate_stage(self):
        if 'stage' in self.df.columns:
            def is_invalid(x):
                if pd.isna(x):
                    return "Valor nulo"
                elif isinstance(x, (int, float)):
                    if x == 0:
                        return "Número 0"
                    elif not (1 <= x <= 12):
                        return "Número fora da faixa 1-12"
                elif isinstance(x, str):
                    if x.strip().upper() == "ERRO":
                        return "Texto 'ERRO'"
                    elif x.strip().upper() != "CONV":
                        return "Texto diferente de 'CONV'"
                return None
            
            mask = self.df['stage'].apply(lambda x: is_invalid(x) is not None)
            if mask.any():
                self.add_error('stage', 'Valores inválidos', mask)
        return self
    
    def validate_modalidade(self):
        if 'modalidade' in self.df.columns:
            mask = (
                self.df['modalidade'].isna() | 
                self.df['modalidade'].apply(lambda x: isinstance(x, (int, float))) |
                self.df['modalidade'].apply(lambda x: str(x).strip() == "")
            )
            if mask.any():
                self.add_error('modalidade', 'Valores inválidos', mask)
        return self
    
    def validate_grupo(self):
        if 'grupo' in self.df.columns:
            mask = (
                self.df['grupo'].isna() | 
                self.df['grupo'].apply(lambda x: isinstance(x, (int, float))) |
                self.df['grupo'].apply(lambda x: str(x).strip() == "")
            )
            if mask.any():
                self.add_error('grupo', 'Valores inválidos', mask)
        return self
    
    def validate_n_aulas(self):
        if 'n aulas' in self.df.columns:
            mask = self.df['n aulas'].apply(lambda x: isinstance(x, str))
            if mask.any():
                self.add_error('n aulas', 'Valores em formato de texto', mask)
        return self
    
    def validate_teacher(self):
        if 'teacher' in self.df.columns:
            mask = (
                self.df['teacher'].isna() | 
                self.df['teacher'].apply(lambda x: isinstance(x, (int, float))) |
                self.df['teacher'].apply(lambda x: str(x).strip() == "")
            )
            if mask.any():
                self.add_error('teacher', 'Valores inválidos', mask)
        return self
    
    def validate_status(self):
        if 'status' in self.df.columns:
            mask = (
                self.df['status'].isna() | 
                self.df['status'].apply(lambda x: isinstance(x, (int, float))) |
                self.df['status'].apply(lambda x: str(x).strip() == "")
            )
            if mask.any():
                self.add_error('status', 'Valores inválidos', mask)
        return self
    
    def validate_all(self):
        """Executa todas as validações"""
        return (self
                .validate_nome_grupo()
                .validate_horario()
                .validate_unidade()
                .validate_dias_semana()
                .validate_stage()
                .validate_modalidade()
                .validate_grupo()
                .validate_n_aulas()
                .validate_teacher()
                .validate_status())