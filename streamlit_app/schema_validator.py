import pandas as pd
import pandera as pa

def get_schema():
    return pa.DataFrameSchema({
        'nome grupo': pa.Column(
            dtype=str,
            unique=True,
            nullable=False,
            checks=[
                pa.Check(lambda x: not isinstance(x, (int, float)), error="Não pode ser valor numérico"),
                pa.Check(lambda x: str(x).strip() != "", error="Não pode ser vazio"),
                pa.Check(lambda x: isinstance(x, str) and pd.notna(x), error="Deve ser texto válido")
            ]
        ),
        'horario': pa.Column(
            dtype=object,
            nullable=False,
            checks=[
                pa.Check(lambda x: not isinstance(x, str), error="Valores textuais não são permitidos"),
                pa.Check(lambda x: pd.to_datetime(x, errors='coerce') is not pd.NaT, error="Formato de data/hora inválido"),
                pa.Check(lambda x: not pd.isna(x), error="Não pode ser vazio")
            ]
        ),
        'unidade': pa.Column(
            dtype=str,
            nullable=False,
            checks=[
                pa.Check(lambda x: not isinstance(x, (int, float)), error="Não pode ser valor numérico"),
                pa.Check(lambda x: str(x).strip() != "", error="Não pode ser vazio"),
                pa.Check(lambda x: str(x).strip().title() in ["Satélite", "Jardim", "Vicentina"], 
                        error='Deve ser "Satélite", "Jardim" ou "Vicentina"')
            ]
        ),
        'dias da semana': pa.Column(
            dtype=str,
            nullable=False,
            checks=[
                pa.Check(lambda x: not isinstance(x, (int, float)), error="Não pode ser valor numérico"),
                pa.Check(lambda x: str(x).strip() != "", error="Não pode ser vazio"),
                pa.Check(lambda x: isinstance(x, str) and pd.notna(x), error="Deve ser texto válido")
            ]
        ),
        'stage': pa.Column(
            dtype=object,
            nullable=False,
            checks=[
                pa.Check(lambda x: not pd.isna(x), error="Não pode ser vazio"),
                pa.Check(lambda x: not isinstance(x, (int, float)) or (x != 0 and 1 <= x <= 12), 
                        error="Números devem ser 1-12 e ≠ 0"),
                pa.Check(lambda x: not isinstance(x, str) or (x.strip().upper() == "CONV" and x.strip().upper() != "ERRO"), 
                        error='Texto deve ser "CONV" e nunca "ERRO"')
            ]
        ),
        'modalidade': pa.Column(
            dtype=str,
            nullable=False,
            checks=[
                pa.Check(lambda x: not isinstance(x, (int, float)), error="Não pode ser valor numérico"),
                pa.Check(lambda x: str(x).strip() != "", error="Não pode ser vazio"),
                pa.Check(lambda x: isinstance(x, str) and pd.notna(x), error="Deve ser texto válido")
            ]
        ),
        'grupo': pa.Column(
            dtype=str,
            nullable=False,
            checks=[
                pa.Check(lambda x: not isinstance(x, (int, float)), error="Não pode ser valor numérico"),
                pa.Check(lambda x: str(x).strip() != "", error="Não pode ser vazio"),
                pa.Check(lambda x: isinstance(x, str) and pd.notna(x), error="Deve ser texto válido")
            ]
        ),
        'n aulas': pa.Column(
            dtype=object,
            nullable=False,
            checks=[
                pa.Check(lambda x: not isinstance(x, str), error="Valores textuais como 'DEZ' não são permitidos"),
                pa.Check(lambda x: pd.api.types.is_integer(x), error="Deve ser um número inteiro"),
                pa.Check(lambda x: not pd.isna(x), error="Não pode ser vazio")
            ]
        ),
        'teacher': pa.Column(
            dtype=str,
            nullable=False,
            checks=[
                pa.Check(lambda x: not isinstance(x, (int, float)), error="Não pode ser valor numérico"),
                pa.Check(lambda x: str(x).strip() != "", error="Não pode ser vazio"),
                pa.Check(lambda x: isinstance(x, str) and pd.notna(x), error="Deve ser texto válido")
            ]
        ),
        'status': pa.Column(
            dtype=str,
            nullable=False,
            checks=[
                pa.Check(lambda x: not isinstance(x, (int, float)), error="Não pode ser valor numérico"),
                pa.Check(lambda x: str(x).strip() != "", error="Não pode ser vazio"),
                pa.Check(lambda x: isinstance(x, str) and pd.notna(x), error="Deve ser texto válido")
            ]
        ),
    })