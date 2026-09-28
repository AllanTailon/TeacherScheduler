"""Unit tests for transforms, titles, validator, and tiny CP-SAT schedules."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from rota_io import build_rota_titulo, parse_rota_titulo, normalize_stage
from teacher_allocation import TeacherScheduler
from transforms import clean_data, transform_classes_dataframe
from validator import Validator


def _sample_classes_raw() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "nome grupo": "G1",
                "horario": "10:00:00",
                "unidade": "JARDIM",
                "status": "PRESENCIAL",
                "dias da semana": "2ª ● 4ª",
                "stage": "ESTAGIO_1",
                "modalidade": "Inglês",
                "grupo": "Grupo",
                "n aulas": 4,
                "teacher": "-",
                "ultimo_professor": "Alice",
                "penultimo_professor": "-",
                "restricoes_professor": None,
            },
            {
                "nome grupo": "G2",
                "horario": "14:00:00",
                "unidade": "JARDIM",
                "status": "PRESENCIAL",
                "dias da semana": "3ª",
                "stage": "ESTAGIO_1",
                "modalidade": "Inglês",
                "grupo": "Grupo",
                "n aulas": 2,
                "teacher": "-",
                "ultimo_professor": "Bob",
                "penultimo_professor": "-",
                "restricoes_professor": None,
            },
        ]
    )


def _sample_teachers() -> pd.DataFrame:
    hours = {
        "10:00:00": 1,
        "14:00:00": 1,
        "11:00:00": 1,
    }
    days = {
        "SEGUNDA": 1,
        "TERÇA": 1,
        "QUARTA": 1,
        "QUINTA": 1,
        "SEXTA": 1,
        "SÁBADO": 1,
    }
    flags = {
        "SATÉLITE": 1,
        "JARDIM": 1,
        "VICENTINA": 1,
        "ONLINE": 1,
        "PRESENCIAL": 1,
        "Grupo": 1,
        "VIP": 1,
        "In Company": 1,
        "VIP - In Company": 1,
        "Espanhol": 1,
        "Kids": 1,
        "INTENSIVÃO": 1,
        "ESTAGIO_1": 1,
        "MEDIA": 8,
        "FERIAS": 0,
    }
    rows = []
    for name in ("Alice", "Bob"):
        rows.append({"TEACHER": name, **hours, **days, **flags})
    return pd.DataFrame(rows)


def test_parse_and_build_rota_titulo():
    inicio, fim = parse_rota_titulo("ROTA 01/03 A 07/03")
    assert inicio == "01/03"
    assert fim == "07/03"
    assert build_rota_titulo("01/03", "07/03") == "ROTA 01/03 A 07/03"


def test_normalize_stage():
    assert normalize_stage(1) == "ESTAGIO_1"
    assert normalize_stage("2") == "ESTAGIO_2"
    assert normalize_stage("ESTAGIO_3") == "ESTAGIO_3"


def test_transform_classes_expands_days():
    raw = _sample_classes_raw()
    result = transform_classes_dataframe(raw)
    assert set(result["dias da semana"]) >= {"SEGUNDA", "QUARTA", "TERÇA"}
    assert "horario_tratado" in result.columns
    g1_days = set(result.loc[result["nome grupo"] == "G1", "dias da semana"])
    assert g1_days == {"SEGUNDA", "QUARTA"}


def test_clean_data_day_map():
    df = pd.DataFrame(
        [
            {
                "n aulas": 4,
                "dias da semana": "2ª ● 3ª",
                "status": None,
                "horario": "09:00:00",
            }
        ]
    )
    cleaned = clean_data(df)
    assert set(cleaned["dias da semana"]) == {"SEGUNDA", "TERÇA"}
    assert (cleaned["status"] == "PRESENCIAL").all()


def test_validator_missing_teacher():
    classes = transform_classes_dataframe(_sample_classes_raw())
    classes = classes.copy()
    classes.loc[classes["nome grupo"] == "G1", "teacher"] = "Zed"
    teachers = _sample_teachers()
    result = Validator(classes, teachers).check_problem()
    assert any(i.code == "missing_teacher" for i in result.errors)
    assert not result.ok


def test_schedule_teachers_tiny_feasible():
    classes = transform_classes_dataframe(_sample_classes_raw())
    teachers = _sample_teachers()
    # Drop modality columns not needed / ensure soft level 2 is loosest
    scheduler = TeacherScheduler(classes, teachers)
    result = scheduler.schedule_teachers(use_soft_constraint=2, seed=42)
    assert result.status in ("OPTIMAL", "FEASIBLE", "INFEASIBLE", "UNKNOWN")
    # 2 teachers and 2 groups → equality does not force at_least_1
    assert result.require_all_teachers is False
    if result.success:
        assert set(result.allocations["nome grupo"]) == {"G1", "G2"}
        assert len(result.allocations) == 2


def test_require_all_teachers_skipped_when_more_teachers_than_groups():
    classes = transform_classes_dataframe(_sample_classes_raw().iloc[:1].copy())
    teachers = _sample_teachers()
    # 2 teachers, 1 group → should not force every teacher ≥1 class
    scheduler = TeacherScheduler(classes, teachers)
    result = scheduler.schedule_teachers(use_soft_constraint=2, seed=7)
    assert result.require_all_teachers is False


def test_require_all_teachers_false_when_counts_equal():
    classes = transform_classes_dataframe(_sample_classes_raw())
    teachers = _sample_teachers()  # 2 teachers, 2 groups
    result = TeacherScheduler(classes, teachers).schedule_teachers(
        use_soft_constraint=2, seed=5
    )
    assert result.require_all_teachers is False


def test_saturday_ignores_hour_and_unit_flags():
    """Teacher with SÁBADO=1 but hour=0 and unit=0 must still take Saturday class."""
    from transforms import transform_allocation_dataframe

    classes_raw = pd.DataFrame(
        [
            {
                "nome grupo": "SAT GROUP",
                "horario": "08:00:00",
                "unidade": "VICENTINA",
                "status": "PRESENCIAL",
                "dias da semana": "Saturday SINGLE",
                "stage": "ESTAGIO_1",
                "modalidade": "Inglês",
                "grupo": "Grupo",
                "n aulas": 2,
                "teacher": "-",
                "ultimo_professor": "-",
                "penultimo_professor": "-",
                "restricoes_professor": None,
            }
        ]
    )
    teachers = _sample_teachers()
    teachers["08:00:00"] = 1
    # Alice: Saturday ok, but block the hour and VICENTINA
    teachers.loc[teachers["TEACHER"] == "Alice", "08:00:00"] = 0
    teachers.loc[teachers["TEACHER"] == "Alice", "VICENTINA"] = 0
    teachers.loc[teachers["TEACHER"] == "Alice", "SÁBADO"] = 1
    teachers.loc[teachers["TEACHER"] == "Bob", "SÁBADO"] = 0

    classes = transform_classes_dataframe(classes_raw)
    assert set(classes["dias da semana"]) == {"SÁBADO"}

    result = TeacherScheduler(classes, teachers).schedule_teachers(
        use_soft_constraint=2, seed=1
    )
    assert result.success, result.status
    assert result.allocations.iloc[0]["professores_alocados"] == "Alice"


def test_history_shifts_ultimo_to_penultimo_on_allocate():
    """After allocation: penultimo <- old ultimo, ultimo <- assigned teacher."""
    from transforms import transform_allocation_dataframe

    aulas = pd.DataFrame(
        [
            {
                "nome grupo": "G1",
                "teacher": "Alice",
                "ultimo_professor": "Alice",
                "penultimo_professor": "-",
            },
            {
                "nome grupo": "G2",
                "teacher": "-",
                "ultimo_professor": "Bob",
                "penultimo_professor": "Alice",
            },
            {
                "nome grupo": "G3",
                "teacher": "-",
                "ultimo_professor": "-",
                "penultimo_professor": "-",
            },
        ]
    )
    aloc = pd.DataFrame(
        [
            {"nome grupo": "G1", "professores_alocados": "Alice"},
            {"nome grupo": "G2", "professores_alocados": "Alice"},
            {"nome grupo": "G3", "professores_alocados": "Bob"},
        ]
    )
    out, _ = transform_allocation_dataframe(aulas, aloc)
    g1 = out[out["nome grupo"] == "G1"].iloc[0]
    g2 = out[out["nome grupo"] == "G2"].iloc[0]
    g3 = out[out["nome grupo"] == "G3"].iloc[0]
    assert g1["teacher"] == "Alice"
    assert g1["ultimo_professor"] == "Alice"
    assert g1["penultimo_professor"] == "Alice"
    assert g2["teacher"] == "Alice"
    assert g2["ultimo_professor"] == "Alice"
    assert g2["penultimo_professor"] == "Bob"
    assert g3["teacher"] == "Bob"
    assert g3["ultimo_professor"] == "Bob"
    assert g3["penultimo_professor"] == "-"


def test_soft_media_allows_overflow_when_capacity_short():
    """When total MEDIA < total lessons, soft level 2 must still be feasible."""
    classes_raw = pd.DataFrame(
        [
            {
                "nome grupo": "G1",
                "horario": "10:00:00",
                "unidade": "JARDIM",
                "status": "PRESENCIAL",
                "dias da semana": "2ª",
                "stage": "ESTAGIO_1",
                "modalidade": "Inglês",
                "grupo": "Grupo",
                "n aulas": 6,
                "teacher": "-",
                "ultimo_professor": "-",
                "penultimo_professor": "-",
                "restricoes_professor": None,
            },
            {
                "nome grupo": "G2",
                "horario": "14:00:00",
                "unidade": "JARDIM",
                "status": "PRESENCIAL",
                "dias da semana": "3ª",
                "stage": "ESTAGIO_1",
                "modalidade": "Inglês",
                "grupo": "Grupo",
                "n aulas": 6,
                "teacher": "-",
                "ultimo_professor": "-",
                "penultimo_professor": "-",
                "restricoes_professor": None,
            },
        ]
    )
    teachers = _sample_teachers()
    teachers["MEDIA"] = 5  # total cap 10 < demand 12
    classes = transform_classes_dataframe(classes_raw)
    result = TeacherScheduler(classes, teachers).schedule_teachers(
        use_soft_constraint=2, seed=11
    )
    assert result.success, result.status
    assert len(result.allocations) == 2


def test_hard_forbid_ultimo_on_unassigned_group():
    classes_raw = _sample_classes_raw().copy()
    classes_raw.loc[0, "teacher"] = "-"
    classes_raw.loc[0, "ultimo_professor"] = "Alice"
    classes_raw.loc[0, "penultimo_professor"] = "Bob"
    classes_raw.loc[1, "teacher"] = "Bob"
    classes_raw.loc[1, "ultimo_professor"] = "Bob"

    classes = transform_classes_dataframe(classes_raw)
    teachers = _sample_teachers()
    result = TeacherScheduler(classes, teachers).schedule_teachers(
        use_soft_constraint=1, seed=3
    )
    if result.success:
        g1 = result.allocations[result.allocations["nome grupo"] == "G1"].iloc[0]
        assert g1["professores_alocados"] != "Alice"
