"""Class/teacher DataFrame transforms for the solver pipeline."""

from __future__ import annotations

import re

import pandas as pd

from constants import DAY_SUBSTITUTIONS, INTENSIVE_LESSON_THRESHOLD, MODALITY_ALIASES
from rota_io import normalize_stage, normalize_teacher_name, stringify_column_name, teacher_or_dash

# Day token + optional intensifier, e.g. "2ª TRIPLE", "6ª DOUBLE", "Saturday TRIPLE"
_DAY_TOKEN_RE = re.compile(
    r"(EVERYDAY|SATURDAY|2ª|3ª|4ª|5ª|6ª)(?:\s*(TRIPLE|DOUBLE|SINGLE))?",
    flags=re.IGNORECASE,
)


def _intensifier_hours(token: str | None) -> int:
    if not token:
        return 1
    upper = token.upper()
    if upper == "TRIPLE":
        return 3
    if upper == "DOUBLE":
        return 2
    return 1


def parse_day_slots(dias: str) -> list[tuple[str, int]]:
    """Parse '2ª TRIPLE 6ª DOUBLE' into [(2ª, 3), (6ª, 2)]."""
    text = str(dias).replace("●", " ").replace("-", " ")
    slots: list[tuple[str, int]] = []
    for day_raw, intensifier in _DAY_TOKEN_RE.findall(text):
        hours = _intensifier_hours(intensifier)
        day_key = day_raw.upper() if day_raw.upper() in {"SATURDAY", "EVERYDAY"} else day_raw
        if day_key == "EVERYDAY":
            for weekday in ("2ª", "3ª", "4ª", "5ª", "6ª"):
                slots.append((weekday, hours))
        else:
            slots.append((day_key, hours))
    return slots


def expand_class_row(row: pd.Series) -> pd.DataFrame:
    """Expand one class into one row per (day, consecutive hour)."""
    slots = parse_day_slots(row["dias da semana"])
    if not slots:
        # Fallback: keep row as-is so downstream can still surface the bad day string
        return pd.DataFrame([row])

    hora_inicial = pd.to_datetime(row["horario"], format="%H:%M:%S")
    novas = []
    for day, times in slots:
        for i in range(times):
            nova = row.copy()
            nova["horario"] = (hora_inicial + pd.Timedelta(hours=i)).strftime("%H:%M:%S")
            nova["dias da semana"] = day
            novas.append(nova)
    return pd.DataFrame(novas)


def expand_rows(df: pd.DataFrame, func) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    return pd.concat(df.apply(func, axis=1).tolist(), ignore_index=True)


def replicate_row(row: pd.Series, times: int) -> pd.DataFrame:
    """Legacy helper kept for utils facade compatibility."""
    hora_inicial = pd.to_datetime(row["horario"], format="%H:%M:%S")
    novas_linhas = []
    for i in range(times):
        nova_linha = row.copy()
        nova_linha["horario"] = (hora_inicial + pd.Timedelta(hours=i)).strftime("%H:%M:%S")
        novas_linhas.append(nova_linha)
    return pd.DataFrame(novas_linhas)


def base_selection(df: pd.DataFrame) -> tuple:
    """Legacy helper: split simple / DOUBLE / TRIPLE rows (pre per-day parser)."""
    aulas = df.loc[~df["nome grupo"].isnull()].copy()
    aulas["dias da semana"] = aulas["dias da semana"].astype(str).str.upper()
    aulas["dias da semana"] = aulas["dias da semana"].str.replace(
        "EVERYDAY", "2ª ● 3ª ● 4ª ● 5ª ● 6ª"
    )
    tri = aulas.loc[aulas["dias da semana"].str.contains("TRIPLE")]
    doub = aulas.loc[aulas["dias da semana"].str.contains("DOUBLE")]
    aulas_simples = aulas[~aulas["dias da semana"].str.contains("DOUBLE|TRIPLE")].copy()
    aulas_simples["horario"] = pd.to_datetime(
        aulas_simples["horario"], format="%H:%M:%S"
    ).dt.strftime("%H:%M:%S")
    return aulas_simples, doub, tri


def finalize_class_rows(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["dias da semana"] = df["dias da semana"].replace(DAY_SUBSTITUTIONS, regex=True)
    df["dias da semana"] = df["dias da semana"].astype(str).str.upper()
    df["status"] = df["status"].fillna("PRESENCIAL")
    df["horario_tratado"] = pd.to_datetime(df["horario"], format="%H:%M:%S")
    df["is_intensive"] = (df["n aulas"] >= INTENSIVE_LESSON_THRESHOLD).astype(int)
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Legacy helper: explode multi-day strings without DOUBLE/TRIPLE, then finalize."""
    df = df.copy()
    df["dias da semana"] = (
        df["dias da semana"]
        .astype(str)
        .str.replace("●", ",", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace("-", "", regex=False)
        .str.replace("DOUBLE", ",", regex=False)
        .str.replace("SINGLE", "", regex=False)
        .str.replace("TRIPLE", "", regex=False)
        .str.split(",")
    )
    df = df.explode("dias da semana").reset_index(drop=True)
    df["dias da semana"] = df["dias da semana"].str.replace("ª", "ª,", regex=False).str.split(",")
    df = df.explode("dias da semana").reset_index(drop=True)
    df = df[df["dias da semana"] != ""].copy()
    return finalize_class_rows(df)


def _prep_classes(aulas_raw: pd.DataFrame) -> pd.DataFrame:
    aulas = aulas_raw.loc[~aulas_raw["nome grupo"].isnull()].copy()
    aulas["dias da semana"] = aulas["dias da semana"].astype(str)
    aulas["stage"] = aulas["stage"].apply(normalize_stage)
    aulas["ultimo_professor"] = aulas["ultimo_professor"].map(teacher_or_dash)
    aulas["penultimo_professor"] = aulas["penultimo_professor"].map(teacher_or_dash)
    aulas["teacher"] = aulas["teacher"].map(teacher_or_dash)
    if "modalidade" in aulas.columns:
        aulas["modalidade"] = aulas["modalidade"].replace(MODALITY_ALIASES)
    aulas["horario"] = pd.to_datetime(aulas["horario"], format="%H:%M:%S").dt.strftime("%H:%M:%S")
    return aulas


def transform_classes_dataframe(aulas_raw):
    aulas = _prep_classes(aulas_raw)
    expanded = expand_rows(aulas, expand_class_row)
    return finalize_class_rows(expanded)


# Backward-compatible alias (typo in original API)
transform_classes_dateframe = transform_classes_dataframe


_TEACHER_TEXT_COLUMNS = frozenset(
    {"TEACHER", "Email", "EMAIL", "E-mail", "e-mail", "email"}
)


def _coerce_teacher_capability_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure 0/1 flags are numeric so comparisons like ``== 0`` work.

    Excel/pandas sometimes load zeros as the string ``\"0\"``, which breaks
    ``df[col] == 0`` and silently skips ONLINE/PRESENCIAL (and other) constraints.
    """
    df = df.copy()
    for col in df.columns:
        if col in _TEACHER_TEXT_COLUMNS:
            continue
        df[col] = pd.to_numeric(df[col], errors="coerce")
        if col != "MEDIA":
            df[col] = df[col].fillna(0).astype(int)
    return df


def transform_teacher_dataframe(professores_raw):
    professores_raw = professores_raw.copy()
    professores_raw.columns = [stringify_column_name(col) for col in professores_raw.columns]
    professores_raw = _coerce_teacher_capability_columns(professores_raw)
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
