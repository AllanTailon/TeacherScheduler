"""Local allocation diagnostics against sample/ Excel files.

Mirrors the exploratory flow from alocacao/notebook_test.ipynb +
constraint ablation from notebook_diagnostico_alocacao.ipynb.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "streamlit_app"
sys.path.insert(0, str(APP))

import pandas as pd
from ortools.sat.python import cp_model

from constants import SATURDAY, SOFT_LEVELS
from rota_io import load_rota_excel
from teacher_allocation import STATUS_NAME, TeacherScheduler
from transforms import transform_classes_dataframe, transform_teacher_dataframe
from validator import Validator

SAMPLE_ROTA = ROOT / "sample" / "rota.xlsx"
SAMPLE_TEACHERS = ROOT / "sample" / "professor.xlsx"


def load_samples(clear_teachers: bool = True, keep_history: bool = False):
    rota, titulo, sheet = load_rota_excel(SAMPLE_ROTA)
    teachers = transform_teacher_dataframe(pd.read_excel(SAMPLE_TEACHERS))
    rota = rota.copy()
    if keep_history:
        rota["ultimo_professor"] = rota["teacher"]
        rota["penultimo_professor"] = "-"
    if clear_teachers:
        rota["teacher"] = "-"
        if not keep_history:
            rota["ultimo_professor"] = "-"
            rota["penultimo_professor"] = "-"
    classes = transform_classes_dataframe(rota)
    return rota, teachers, classes, titulo, sheet


def run_soft_ladder(classes, teachers, seed: int = 42, label: str = ""):
    print(f"\n=== Soft ladder {label} ===")
    scheduler = TeacherScheduler(classes, teachers)
    last = None
    for level in SOFT_LEVELS:
        t0 = time.time()
        result = scheduler.schedule_teachers(use_soft_constraint=level, seed=seed)
        dt = time.time() - t0
        print(
            f" soft={level} status={result.status} n={len(result.allocations)} "
            f"require_all={result.require_all_teachers} t={dt:.1f}s"
        )
        last = result
        if result.success:
            return result
    return last


def ablation(classes, teachers, max_time: float = 20.0):
    print("\n=== Constraint ablation ===")
    ts = TeacherScheduler(classes, teachers)
    ts.create_model()
    ts.create_variables()
    steps = [
        ("pre_aloc", ts.add_teacher_pre_alocation),
        ("teacher_le1", ts.add_teacher_constraints),
        ("schedule", ts.add_schedule_constraints),
        ("unidade", ts.add_unidade_constraints),
        ("gap50", ts.add_impossible_group_constraints),
        ("consec_unit", ts.add_consecutive_group_constraints),
        ("modalidade", ts.add_modalidades_constraints),
        ("grupo", ts.add_grupo_constraints),
        ("estagio", ts.add_estagio_constraints),
        ("online", ts.add_online_constraints),
        ("time", ts.add_time_constraints),
        ("intensive", ts.add_intensive_constraints),
        ("restricoes", ts.add_restrictions_constraints),
        ("fill_all", ts.add_all_class_fill_constraints),
    ]
    if len(ts.teachers) <= len(ts.groups):
        steps.append(("at_least_1", ts.teacher_at_least_1_class_constraints))
    steps.append(("soft2_media_cap", ts.add_class_per_teacher_constraints_double_weighted))

    for name, fn in steps:
        fn()
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = max_time
        solver.parameters.random_seed = 42
        t0 = time.time()
        status = solver.Solve(ts.model)
        print(f" {name:16} {STATUS_NAME.get(status, status):12} t={time.time() - t0:.1f}s")
        if STATUS_NAME.get(status) == "INFEASIBLE":
            break


def soft_by_day(classes, teachers, seed: int = 42):
    print("\n=== Soft ladder by day ===")
    for day in ["SEGUNDA", "TERÇA", "QUARTA", "QUINTA", "SEXTA", SATURDAY]:
        df_day = classes[classes["dias da semana"] == day]
        if df_day.empty:
            continue
        line = f" {day}: groups={df_day['nome grupo'].nunique()}"
        scheduler = TeacherScheduler(df_day, teachers)
        for level in SOFT_LEVELS:
            result = scheduler.schedule_teachers(use_soft_constraint=level, seed=seed)
            line += f" | soft{level}={result.status}({len(result.allocations)})"
            if result.success:
                break
        print(line)


def main():
    rota_raw, _, classes_raw, titulo, _ = load_samples(clear_teachers=False)
    print(f"Rota: {titulo}")
    print(
        f"Groups={classes_raw['nome grupo'].nunique()} "
        f"teachers_prefilled={(rota_raw['teacher'] != '-').sum()}/{len(rota_raw)}"
    )

    teachers = transform_teacher_dataframe(pd.read_excel(SAMPLE_TEACHERS))
    demand = int(classes_raw.drop_duplicates("nome grupo")["n aulas"].sum())
    capacity = int(teachers["MEDIA"].sum())
    print(f"Demand n_aulas={demand} | Capacity MEDIA_sum={capacity} | deficit={demand - capacity}")

    validation = Validator(classes_raw, teachers).check_problem()
    print(f"Validation errors={len(validation.errors)} warnings={len(validation.warnings)}")
    for issue in validation.errors[:8]:
        print(f"  ERR [{issue.code}] {issue.message[:160]}")

    # As-is (usually infeasible when prefill has conflicts)
    run_soft_ladder(classes_raw, teachers, label="as-is prefilled")

    # Cleared teachers
    _, teachers, classes_clear, _, _ = load_samples(clear_teachers=True, keep_history=False)
    ablation(classes_clear, teachers)
    run_soft_ladder(classes_clear, teachers, label="cleared teachers")
    soft_by_day(classes_clear, teachers)

    # Saturday rotation check
    sab_groups = set(classes_clear.loc[classes_clear["dias da semana"] == SATURDAY, "nome grupo"])
    rota_sab = rota_raw[rota_raw["nome grupo"].isin(sab_groups)].copy()
    rota_sab["ultimo_professor"] = rota_sab["teacher"]
    rota_sab["penultimo_professor"] = "-"
    rota_sab["teacher"] = "-"
    classes_sab = transform_classes_dataframe(rota_sab)
    result = run_soft_ladder(classes_sab, teachers, label="Saturday-only + history")
    if result and result.success:
        merged = result.allocations.merge(
            rota_sab[["nome grupo", "ultimo_professor"]], on="nome grupo"
        )
        repeats = (merged["professores_alocados"] == merged["ultimo_professor"]).sum()
        print(f" Saturday repeated ultimo: {repeats}/{len(merged)} (soft={result.soft_level})")


if __name__ == "__main__":
    main()
