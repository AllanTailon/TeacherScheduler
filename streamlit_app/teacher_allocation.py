"""CP-SAT teacher-to-group allocation."""

from __future__ import annotations

import random
from dataclasses import dataclass

import pandas as pd
from ortools.sat.python import cp_model

from constants import (
    GROUP_TYPE_LIST,
    INTENSIVE_LESSON_THRESHOLD,
    MEDIA_DEVIATION_DIVISOR,
    MEDIA_HARD_BAND,
    MEDIA_SOFT_OVERFLOW,
    MIDDAY_HOUR,
    MIN_GAP_MINUTES,
    MODALITY_LIST,
    SATURDAY,
    SOLVER_TIME_LIMIT_SECONDS,
    UNIDADE_LIST,
    WEIGHT_MEDIA,
    WEIGHT_MEDIA_OVER,
    WEIGHT_PENULTIMO,
    WEIGHT_REPETICAO,
    WEIGHT_ULTIMO,
)
from rota_io import normalize_teacher_name

STATUS_NAME = {
    cp_model.OPTIMAL: "OPTIMAL",
    cp_model.FEASIBLE: "FEASIBLE",
    cp_model.INFEASIBLE: "INFEASIBLE",
    cp_model.MODEL_INVALID: "MODEL_INVALID",
    cp_model.UNKNOWN: "UNKNOWN",
}


@dataclass
class ScheduleResult:
    allocations: pd.DataFrame
    status: str
    status_code: int
    seed: int
    soft_level: int
    require_all_teachers: bool

    @property
    def success(self) -> bool:
        return self.status in ("OPTIMAL", "FEASIBLE") and not self.allocations.empty


class TeacherScheduler:
    """Assign teachers to class groups with hard/soft OR-Tools CP-SAT constraints."""

    def __init__(self, df_class, df_teach):
        self.df_class = df_class
        self.df_teach = df_teach

    def schedule_teachers(
        self,
        use_soft_constraint: int = 0,
        seed: int | None = None,
        require_all_teachers: bool | None = None,
        # Backward-compatible misspelling
        use_soft_constrait: int | None = None,
    ) -> ScheduleResult:
        if use_soft_constrait is not None:
            use_soft_constraint = use_soft_constrait

        self.create_model()
        self.create_variables()
        self.add_teacher_pre_alocation()
        self.add_teacher_constraints()
        self.add_schedule_constraints()
        self.add_unidade_constraints()
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

        if require_all_teachers is None:
            # Only force every teacher ≥1 group when there are strictly more groups
            # than teachers. Equality would require a perfect matching and often
            # makes day-subsets (e.g. SEXTA) infeasible.
            require_all_teachers = len(self.teachers) < len(self.groups)
        if require_all_teachers:
            self.teacher_at_least_1_class_constraints()

        if use_soft_constraint == 0:
            self.add_class_per_teacher_constraints_hard()
            self.add_history_teacher_objective()
        elif use_soft_constraint == 1:
            self.add_class_per_teacher_constraints_weighted()
            self.add_consecutive_teacher_constraints()
        elif use_soft_constraint == 2:
            self.add_class_per_teacher_constraints_double_weighted()
        else:
            raise ValueError(
                f"use_soft_constraint must be 0, 1, or 2 (got {use_soft_constraint})"
            )

        return self.solve(
            seed=seed,
            soft_level=use_soft_constraint,
            require_all_teachers=require_all_teachers,
        )

    def create_model(self):
        self.alocacoes = {}
        self.model = cp_model.CpModel()

    def create_variables(self):
        self.teachers = self.df_teach["TEACHER"].unique()
        self.groups = self.df_class["nome grupo"].unique()
        self.group_rows = {
            g: self.df_class[self.df_class["nome grupo"] == g] for g in self.groups
        }
        self.group_lessons = {
            g: int(self.group_rows[g]["n aulas"].iloc[0]) for g in self.groups
        }

        for i in self.teachers:
            for g in self.groups:
                self.alocacoes[(i, g)] = self.model.NewBoolVar(f"{i}_converinglesson_{g}")

    def add_teacher_pre_alocation(self):
        for i in self.teachers:
            for g in self.df_class.loc[self.df_class["teacher"] == i, "nome grupo"].unique():
                self.model.Add(self.alocacoes[(i, g)] == 1)

    def add_teacher_constraints(self):
        # Redundant with add_all_class_fill_constraints (==1) but kept for clarity.
        for g in self.groups:
            self.model.Add(sum(self.alocacoes[(i, g)] for i in self.teachers) <= 1)

    def add_schedule_constraints(self):
        for h in self.df_class["horario"].unique():
            for d in self.df_class["dias da semana"].unique():
                grupos_no_mesmo_horario = self.df_class.loc[
                    (self.df_class["horario"] == h) & (self.df_class["dias da semana"] == d)
                ]["nome grupo"].unique()

                for i in self.teachers:
                    self.model.Add(
                        sum(self.alocacoes[(i, g)] for g in grupos_no_mesmo_horario) <= 1
                    )

    def add_unidade_constraints(self):
        """Block unit flags for weekday presencial only.

        Saturday classes ignore unidade: availability is gated only by SÁBADO=1.
        """
        for und in UNIDADE_LIST:
            if und not in self.df_teach.columns:
                continue
            for i in self.df_teach.loc[self.df_teach[und] == 0, "TEACHER"].to_list():
                for g in self.df_class.loc[
                    (
                        (self.df_class["unidade"].str.upper() == und)
                        & (self.df_class["status"] == "PRESENCIAL")
                        & (self.df_class["dias da semana"] != SATURDAY)
                    ),
                    "nome grupo",
                ].unique():
                    self.model.Add(self.alocacoes[(i, g)] == 0)

    def add_impossible_group_constraints(self):
        gap = pd.Timedelta(f"{int(MIN_GAP_MINUTES)} minutes")
        for x in self.df_class["dias da semana"].unique():
            turmas_do_dia = (
                self.df_class.loc[
                    self.df_class["dias da semana"] == x, ["nome grupo", "horario_tratado"]
                ]
                .drop_duplicates(subset=["nome grupo", "horario_tratado"])
                .sort_values("horario_tratado")
                .reset_index(drop=True)
            )

            for idx, turma_1 in turmas_do_dia.iterrows():
                for idx_2 in range(idx + 1, len(turmas_do_dia)):
                    turma_2 = turmas_do_dia.iloc[idx_2]

                    if turma_1["nome grupo"] == turma_2["nome grupo"]:
                        continue

                    diferenca_horario = turma_2["horario_tratado"] - turma_1["horario_tratado"]

                    if diferenca_horario > gap:
                        break

                    if diferenca_horario <= pd.Timedelta(minutes=0):
                        continue

                    grupo_1 = turma_1["nome grupo"]
                    grupo_2 = turma_2["nome grupo"]

                    for i in self.teachers:
                        self.model.Add(
                            self.alocacoes[(i, grupo_1)] + self.alocacoes[(i, grupo_2)] <= 1
                        )

    def add_consecutive_group_constraints(self):
        """Forbid same teacher on different presencial units in the same half-day.

        Saturday is excluded: unidade is ignored for Saturday classes.
        """
        midday = pd.to_datetime(f"1900-01-01 {MIDDAY_HOUR:02d}:00:00")
        pares_total = set()
        presencial = self.df_class[
            (self.df_class["status"] == "PRESENCIAL")
            & (self.df_class["dias da semana"] != SATURDAY)
        ]
        for j in presencial["nome grupo"].unique():
            turmas_turnos_diferentes = set()
            for x in presencial["dias da semana"].unique():
                filtro = (self.df_class["nome grupo"] == j) & (self.df_class["dias da semana"] == x)

                if self.df_class.loc[filtro, "unidade"].empty:
                    continue

                unidade, horario = self.df_class.loc[filtro, ["unidade", "horario_tratado"]].values[
                    0
                ]

                if horario.hour <= MIDDAY_HOUR:
                    turmas_turnos_oposto = self.df_class.loc[
                        (self.df_class["dias da semana"] == x)
                        & (self.df_class["horario_tratado"] <= midday)
                        & (self.df_class["status"] == "PRESENCIAL")
                        & (self.df_class["unidade"] != unidade),
                        "nome grupo",
                    ].to_list()
                else:
                    turmas_turnos_oposto = self.df_class.loc[
                        (self.df_class["dias da semana"] == x)
                        & (self.df_class["horario_tratado"] > midday)
                        & (self.df_class["status"] == "PRESENCIAL")
                        & (self.df_class["unidade"] != unidade),
                        "nome grupo",
                    ].to_list()
                turmas_turnos_diferentes.update(turmas_turnos_oposto)
            pares_total.update(tuple(sorted([j, t])) for t in turmas_turnos_diferentes)

        for i in self.teachers:
            for t in pares_total:
                self.model.Add(self.alocacoes[(i, t[0])] + self.alocacoes[(i, t[1])] <= 1)

    def _unassigned_groups(self):
        return self.df_class[
            (self.df_class["teacher"] == "-") | (self.df_class["teacher"].isnull())
        ]["nome grupo"].unique()

    def _group_history(self, group_name) -> tuple[str | None, str | None]:
        grupo_info = self.df_class[self.df_class["nome grupo"] == group_name]
        ultimo = normalize_teacher_name(grupo_info["ultimo_professor"].iloc[0])
        penultimo = normalize_teacher_name(grupo_info["penultimo_professor"].iloc[0])
        return ultimo, penultimo

    def add_consecutive_teacher_constraints(self):
        """Hard-forbid repeating ultimo_professor on still-unassigned groups."""
        for g in self._unassigned_groups():
            ultimo, _ = self._group_history(g)
            if ultimo and ultimo in self.teachers:
                self.model.Add(self.alocacoes[(ultimo, g)] == 0)

    def history_teacher_penalties(
        self, weight_ultimo=WEIGHT_ULTIMO, weight_penultimo=WEIGHT_PENULTIMO
    ):
        """Soft penalties: prefer not repeating ultimo (stronger) or penultimo."""
        penalidades = []
        for g in self._unassigned_groups():
            ultimo, penultimo = self._group_history(g)
            if weight_ultimo and ultimo and ultimo in self.teachers:
                penalidades.append(self.alocacoes[(ultimo, g)] * weight_ultimo)
            if (
                weight_penultimo
                and penultimo
                and penultimo in self.teachers
                and penultimo != ultimo
            ):
                penalidades.append(self.alocacoes[(penultimo, g)] * weight_penultimo)
        return penalidades

    def add_history_teacher_objective(
        self, weight_ultimo=WEIGHT_ULTIMO, weight_penultimo=WEIGHT_PENULTIMO
    ):
        penalidades = self.history_teacher_penalties(weight_ultimo, weight_penultimo)
        if penalidades:
            self.model.Minimize(sum(penalidades))

    def add_consecutive_teacher_constraints_soft(self, penalty_weight=None):
        """Backward-compatible wrapper around history soft penalties."""
        weight = WEIGHT_ULTIMO if penalty_weight is None else penalty_weight
        self.add_history_teacher_objective(weight_ultimo=weight, weight_penultimo=WEIGHT_PENULTIMO)

    def add_modalidades_constraints(self):
        for mod in MODALITY_LIST:
            if mod not in self.df_teach.columns:
                continue
            for i in self.df_teach.loc[self.df_teach[mod] == 0, "TEACHER"].to_list():
                for g in self.df_class.loc[self.df_class["modalidade"] == mod, "nome grupo"].unique():
                    self.model.Add(self.alocacoes[(i, g)] == 0)

    def add_grupo_constraints(self):
        for grp in GROUP_TYPE_LIST:
            if grp not in self.df_teach.columns:
                continue
            for i in self.df_teach.loc[self.df_teach[grp] == 0, "TEACHER"].to_list():
                for g in self.df_class.loc[self.df_class["grupo"] == grp, "nome grupo"].unique():
                    self.model.Add(self.alocacoes[(i, g)] == 0)

    def add_class_per_teacher_constraints_hard(self):
        for i in self.teachers:
            media = self.get_teacher_media(i)
            max_aulas_professor = media
            min_aulas_professor = max(0, media - MEDIA_HARD_BAND)

            carga_professor = self.teacher_load_expr(i)
            self.model.Add(carga_professor <= max_aulas_professor)
            self.model.Add(carga_professor >= min_aulas_professor)

    def get_teacher_media(self, teacher):
        return int(self.df_teach.loc[self.df_teach["TEACHER"] == teacher, "MEDIA"].values[0])

    def teacher_load_expr(self, teacher):
        return sum(
            self.alocacoes[(teacher, g)] * self.group_lessons[g] for g in self.groups
        )

    def _soft_media_load_penalties(self, weight_media=WEIGHT_MEDIA, weight_over=WEIGHT_MEDIA_OVER):
        """Allow load up to MEDIA + overflow; penalize under and (more) over MEDIA."""
        total_lessons = sum(self.group_lessons.values()) or 1
        penalties = []

        for i in self.teachers:
            media = self.get_teacher_media(i)
            hard_max = min(total_lessons, media + MEDIA_SOFT_OVERFLOW)
            load = self.model.NewIntVar(0, hard_max, f"aulas_alocadas_{i}")
            # under can be up to `media` when the teacher gets 0 lessons
            under = self.model.NewIntVar(0, media, f"desvio_under_{i}")
            over = self.model.NewIntVar(0, MEDIA_SOFT_OVERFLOW, f"desvio_over_{i}")

            self.model.Add(load == self.teacher_load_expr(i))
            self.model.Add(under >= media - load)
            self.model.Add(over >= load - media)

            scale = max(1, int(media / MEDIA_DEVIATION_DIVISOR))
            penalties.append(under * scale * weight_media + over * scale * weight_over)

        return penalties

    def add_class_per_teacher_constraints_double_weighted(
        self, weight_media=WEIGHT_MEDIA, weight_repeticao=WEIGHT_REPETICAO
    ):
        desvios = self._soft_media_load_penalties(
            weight_media=weight_media, weight_over=WEIGHT_MEDIA_OVER
        )
        # weight_repeticao keeps legacy meaning = soft weight on ultimo
        penalidades = self.history_teacher_penalties(
            weight_ultimo=weight_repeticao,
            weight_penultimo=WEIGHT_PENULTIMO,
        )
        self.model.Minimize(sum(desvios) + sum(penalidades))

    def add_class_per_teacher_constraints_weighted(self):
        desvios = self._soft_media_load_penalties()
        # Soft penultimo only — ultimo is hard-forbidden by add_consecutive_teacher_constraints
        history = self.history_teacher_penalties(weight_ultimo=0, weight_penultimo=WEIGHT_PENULTIMO)
        self.model.Minimize(sum(desvios) + sum(history))
    def add_estagio_constraints(self):
        estagio_list = self.df_class.loc[
            self.df_class["stage"].str.contains("ESTAGIO", na=False)
        ]["stage"].unique()
        for est in estagio_list:
            if est not in self.df_teach.columns:
                continue
            for i in self.df_teach.loc[self.df_teach[est] == 0, "TEACHER"].to_list():
                for g in self.df_class.loc[
                    ((self.df_class["stage"] == est) & (self.df_class["modalidade"] != "Espanhol")),
                    "nome grupo",
                ].unique():
                    self.model.Add(self.alocacoes[(i, g)] == 0)

    def add_online_constraints(self):
        for sts in ["ONLINE", "PRESENCIAL"]:
            if sts not in self.df_teach.columns:
                continue
            for i in self.df_teach.loc[(self.df_teach[sts] == 0), "TEACHER"].to_list():
                for g in self.df_class.loc[self.df_class["status"] == sts]["nome grupo"].unique():
                    self.model.Add(self.alocacoes[(i, g)] == 0)

    def add_time_constraints(self):
        self.add_hour_availability_constraints()
        self.add_day_availability_constraints()

    def add_hour_availability_constraints(self):
        """Enforce teacher hour flags for weekday lessons only.

        Saturday-only groups (and Saturday hours of a group) ignore hour columns;
        day availability SÁBADO=1 is enough.
        """
        for g in self.groups:
            weekday_rows = self.group_rows[g][
                self.group_rows[g]["dias da semana"] != SATURDAY
            ]
            if weekday_rows.empty:
                continue
            time_class = list(weekday_rows["horario"].unique())
            missing = [h for h in time_class if h not in self.df_teach.columns]
            if missing:
                continue
            for i in self.teachers:
                if (self.df_teach.loc[self.df_teach["TEACHER"] == i, time_class] == 0).any(
                    axis=1
                ).values[0]:
                    self.model.Add(self.alocacoes[(i, g)] == 0)

    def add_day_availability_constraints(self):
        for i in self.teachers:
            for x in self.df_class["dias da semana"].unique():
                if x not in self.df_teach.columns:
                    continue
                turmas_do_dia = self.df_class[self.df_class["dias da semana"] == x][
                    "nome grupo"
                ].unique()
                disponibilidade = self.df_teach[self.df_teach["TEACHER"] == i][x].values[0]

                if disponibilidade == 0:
                    for g in turmas_do_dia:
                        self.model.Add(self.alocacoes[(i, g)] == 0)

    def add_intensive_constraints(self):
        if "INTENSIVÃO" not in self.df_teach.columns:
            return
        for i in self.df_teach.loc[self.df_teach["INTENSIVÃO"] == 0, "TEACHER"].to_list():
            for g in self.df_class.loc[
                self.df_class["n aulas"] >= INTENSIVE_LESSON_THRESHOLD, "nome grupo"
            ].unique():
                self.model.Add(self.alocacoes[(i, g)] == 0)

    def add_restrictions_constraints(self):
        for g in self.df_class[self.df_class["restricoes_professor"].notnull()][
            "nome grupo"
        ].unique():
            restricoes_prof = (
                self.df_class[self.df_class["nome grupo"] == g]["restricoes_professor"]
                .unique()[0]
                .split(",")
            )
            for i in restricoes_prof:
                if i in self.teachers:
                    self.model.Add(self.alocacoes[(i, g)] == 0)

    def add_all_class_fill_constraints(self):
        for g in self.groups:
            self.model.Add(sum(self.alocacoes[(i, g)] for i in self.teachers) == 1)

    def teacher_at_least_1_class_constraints(self):
        for i in self.teachers:
            self.model.Add(sum(self.alocacoes[(i, g)] for g in self.groups) >= 1)

    def solve(
        self, seed: int | None, soft_level: int, require_all_teachers: bool
    ) -> ScheduleResult:
        solver = cp_model.CpSolver()

        if seed is None:
            seed = random.randint(1, 10000)
        solver.parameters.random_seed = seed
        solver.parameters.search_branching = cp_model.AUTOMATIC_SEARCH
        solver.parameters.max_time_in_seconds = SOLVER_TIME_LIMIT_SECONDS
        solver.parameters.enumerate_all_solutions = False
        status = solver.Solve(self.model)

        rows = []
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            for g in self.groups:
                for i in self.teachers:
                    if solver.Value(self.alocacoes[(i, g)]):
                        rows.append({"professores_alocados": i, "nome grupo": g})

        allocations = pd.DataFrame(rows, columns=["professores_alocados", "nome grupo"])
        return ScheduleResult(
            allocations=allocations,
            status=STATUS_NAME.get(status, str(status)),
            status_code=int(status),
            seed=seed,
            soft_level=soft_level,
            require_all_teachers=require_all_teachers,
        )
