"""Class/teacher DataFrame transforms for the solver pipeline."""

from __future__ import annotations

import pandas as pd

from constants import DAY_SUBSTITUTIONS, INTENSIVE_LESSON_THRESHOLD
from rota_io import normalize_stage, normalize_teacher_name, stringify_column_name, teacher_or_dash


def replicate_row(row: pd.Series, times: int) -> pd.DataFrame:
    hora_inicial = pd.to_datetime(row["horario"], format="%H:%M:%S")
    novas_linhas = []
    for i in range(times):
        nova_linha = row.copy()
        nova_linha["horario"] = (hora_inicial + pd.Timedelta(hours=i)).strftime("%H:%M:%S")
        novas_linhas.append(nova_linha)
    return pd.DataFrame(novas_linhas)


def expand_rows(df: pd.DataFrame, func) -> pd.DataFrame:
    return pd.concat(df.apply(func, axis=1).tolist(), ignore_index=True)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["dias da semana"] = (
        df["dias da semana"]
        .str.replace("●", ",")
        .str.replace(" ", "")
        .str.replace("-", "")
        .str.replace("DOUBLE", ",")
        .str.replace("SINGLE", "")
        .str.replace("TRIPLE", "")
        .str.split(",")
    )
    df = df.explode("dias da semana").reset_index(drop=True)

    df["dias da semana"] = df["dias da semana"].str.replace("ª", "ª,").str.split(",")
    df = df.explode("dias da semana").reset_index(drop=True)

    df = df[df["dias da semana"] != ""].copy()

    df["dias da semana"] = df["dias da semana"].replace(DAY_SUBSTITUTIONS, regex=True)
    df["status"] = df["status"].fillna("PRESENCIAL")
    df["horario_tratado"] = pd.to_datetime(df["horario"], format="%H:%M:%S")
    df["is_intensive"] = (df["n aulas"] >= INTENSIVE_LESSON_THRESHOLD).astype(int)

    return df


def base_selection(df: pd.DataFrame) -> tuple:
    aulas_tratadas = df.loc[~df["nome grupo"].isnull()]

    aulas = aulas_tratadas.copy()
    aulas["dias da semana"] = aulas["dias da semana"].str.upper()
    aulas["dias da semana"] = aulas["dias da semana"].str.replace(
        "EVERYDAY", "2ª ● 3ª ● 4ª ● 5ª ● 6ª"
    )
    aulas["stage"] = aulas["stage"].apply(normalize_stage)
    aulas["ultimo_professor"] = aulas["ultimo_professor"].map(teacher_or_dash)
    aulas["penultimo_professor"] = aulas["penultimo_professor"].map(teacher_or_dash)
    aulas["teacher"] = aulas["teacher"].map(teacher_or_dash)

    tri = aulas.loc[aulas["dias da semana"].str.contains("TRIPLE")]
    doub = aulas.loc[aulas["dias da semana"].str.contains("DOUBLE")]
    aulas_simples = aulas[~aulas["dias da semana"].str.contains("DOUBLE|TRIPLE")].copy()

    aulas_simples["horario"] = pd.to_datetime(
        aulas_simples["horario"], format="%H:%M:%S"
    ).dt.strftime("%H:%M:%S")
    return aulas_simples, doub, tri


def transform_classes_dataframe(aulas_raw):
    aulas_simples, doub, tri = base_selection(aulas_raw)

    if doub.empty:
        aulas_duplicadas = pd.DataFrame(columns=aulas_simples.columns)
    else:
        aulas_duplicadas = expand_rows(doub, lambda row: replicate_row(row, times=2))

    if tri.empty:
        aulas_triplicadas = pd.DataFrame(columns=aulas_simples.columns)
    else:
        aulas_triplicadas = expand_rows(tri, lambda row: replicate_row(row, times=3))

    df_tratado = pd.concat(
        [aulas_simples, aulas_duplicadas, aulas_triplicadas], ignore_index=True
    )
    return clean_data(df_tratado)


# Backward-compatible alias (typo in original API)
transform_classes_dateframe = transform_classes_dataframe


def transform_teacher_dataframe(professores_raw):
    professores_raw = professores_raw.copy()
    professores_raw.columns = [stringify_column_name(col) for col in professores_raw.columns]
    if professores_raw.columns.str.contains("FERIAS").any():
        professores_raw = professores_raw[professores_raw["FERIAS"] != 1].copy()
    return professores_raw


def transform_allocation_dataframe(aulas_raw, base_alocada):
    """Merge solver output and advance history:

    penultimo <- ultimo (anterior)
    ultimo    <- professor recém-alocado
    """
    allocation_df = pd.merge(aulas_raw, base_alocada, on="nome grupo", how="left")

    old_ultimo = allocation_df["ultimo_professor"].map(normalize_teacher_name)

    assigned_mask = allocation_df["professores_alocados"].notnull()
    allocation_df.loc[assigned_mask, "teacher"] = allocation_df.loc[
        assigned_mask, "professores_alocados"
    ]
    allocation_df.drop(columns=["professores_alocados"], inplace=True)

    new_teachers = allocation_df["teacher"].map(normalize_teacher_name)

    # For every newly assigned group: shift history then set ultimo
    allocation_df.loc[assigned_mask, "penultimo_professor"] = old_ultimo[assigned_mask].map(
        teacher_or_dash
    )
    allocation_df.loc[assigned_mask, "ultimo_professor"] = new_teachers[assigned_mask].map(
        teacher_or_dash
    )

    # Unassigned rows keep prior history cleaned
    keep = ~assigned_mask
    allocation_df.loc[keep, "ultimo_professor"] = old_ultimo[keep].map(teacher_or_dash)
    if "penultimo_professor" in allocation_df.columns:
        allocation_df.loc[keep, "penultimo_professor"] = allocation_df.loc[
            keep, "penultimo_professor"
        ].map(teacher_or_dash)

    allocation_df["teacher"] = allocation_df["teacher"].map(teacher_or_dash)

    not_allocation_df = allocation_df.loc[allocation_df["teacher"] == "-"].copy()
    return allocation_df, not_allocation_df


# Backward-compatible alias
transform_alocation_dataframe = transform_allocation_dataframe
