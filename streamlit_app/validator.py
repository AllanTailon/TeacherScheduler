"""Pre-solve validation of class/teacher DataFrames (Streamlit-independent)."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from constants import DAYS_OF_WEEK, MIN_GAP_MINUTES, SATURDAY


@dataclass
class ValidationIssue:
    code: str
    message: str
    severity: str = "error"  # error | warning


@dataclass
class ValidationResult:
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def add(self, code: str, message: str, severity: str = "error") -> None:
        self.issues.append(ValidationIssue(code=code, message=message, severity=severity))


class Validator:
    """Collect structural / capability issues for pre-allocated classes."""

    def __init__(self, df_class, df_teach):
        self.df_class = df_class
        self.df_teach = df_teach
        self.teacher_alocated = self.df_class[
            (self.df_class["teacher"].notnull())
            & (self.df_class["teacher"].astype(str).str.strip() != "-")
            & (self.df_class["teacher"].astype(str).str.strip().str.lower() != "nan")
        ]["teacher"].unique()
        self.result = ValidationResult()

    def check_problem(self) -> ValidationResult:
        self.result = ValidationResult()
        self.check_existent_teacher()
        self.check_existent_hour()
        self.check_duplicated_class()
        self.check_allowed_time()
        self.check_multiple_classes()
        self.check_impossible_time()
        self.check_modality_group()
        self.check_teach_status()
        self.check_days_of_week()
        self.check_stage()
        self.check_sequence_classes()
        self.validator_min_classes()
        self.check_restrictions_teacher()
        self.check_teacher_class_type()
        self.check_unidade()
        return self.result

    def check_existent_teacher(self):
        teachers = self.df_teach["TEACHER"].unique()
        diff = set(self.teacher_alocated) - set(teachers)
        if diff:
            self.result.add(
                "missing_teacher",
                f"Professor nao encontrado na tabela de professores: {diff}",
            )

    def check_existent_hour(self):
        """Weekday hours must exist as teacher columns; Saturday hours are ignored."""
        weekday = self.df_class[self.df_class["dias da semana"] != SATURDAY]
        horas_aula = weekday["horario"].unique()
        colunas = self.df_teach.columns
        diff = set(horas_aula) - set(colunas)
        turmas_diff = weekday[weekday["horario"].isin(diff)]["nome grupo"].unique()
        if diff:
            self.result.add(
                "missing_hour_column",
                f"Horário nao encontrado na tabela de professores: {diff} para as turmas: {turmas_diff}",
            )

    def check_duplicated_class(self):
        turmas_unicas = self.df_class.drop_duplicates(subset=["nome grupo", "unidade"])
        duplicado_1 = turmas_unicas[turmas_unicas.duplicated(subset=["nome grupo"])][
            "nome grupo"
        ].to_list()
        duplicado_2 = self.df_class[
            self.df_class.duplicated(subset=["nome grupo", "horario", "dias da semana"])
        ]["nome grupo"].to_list()
        duplicado = set(duplicado_1 + duplicado_2)
        if duplicado:
            self.result.add("duplicated_class", f"Turmas duplicadas: {duplicado}")

    def check_allowed_time(self):
        """Validate day/hour capability for pre-assigned teachers.

        Saturday rows only require SÁBADO=1 — hour flags are ignored.
        """
        horarios_nao_permitido = {}
        dia_da_semana_nao_permitido = {}

        for professor in self.teacher_alocated:
            if professor not in self.df_teach["TEACHER"].values:
                continue

            aulas_prof = self.df_class[self.df_class["teacher"] == professor]
            weekday_aulas = aulas_prof[aulas_prof["dias da semana"] != SATURDAY]
            dias = aulas_prof["dias da semana"].unique()

            horarios = weekday_aulas["horario"].unique()
            horarios_existentes = [h for h in horarios if h in self.df_teach.columns]
            dias_existentes = [d for d in dias if d in self.df_teach.columns]

            if horarios_existentes:
                prof_horarios = self.df_teach[self.df_teach["TEACHER"] == professor][
                    horarios_existentes
                ]
                erros_horario = prof_horarios.columns[(prof_horarios == 0).any()].to_list()
                if erros_horario:
                    horarios_nao_permitido[professor] = erros_horario

            if dias_existentes:
                prof_diasemana = self.df_teach[self.df_teach["TEACHER"] == professor][
                    dias_existentes
                ]
                erros_diasemana = prof_diasemana.columns[(prof_diasemana == 0).any()].to_list()
                if erros_diasemana:
                    dia_da_semana_nao_permitido[professor] = erros_diasemana

        if horarios_nao_permitido:
            self.result.add(
                "disallowed_hour",
                f"Horários não permitidos para os professores: {horarios_nao_permitido}",
            )
        if dia_da_semana_nao_permitido:
            self.result.add(
                "disallowed_day",
                f"Dia da semana não permitidos para os professores: {dia_da_semana_nao_permitido}",
            )

    def check_impossible_time(self):
        gap = pd.Timedelta(f"{int(MIN_GAP_MINUTES)} minutes")
        for professor in self.teacher_alocated:
            for diasemana in self.df_class[self.df_class["teacher"] == professor][
                "dias da semana"
            ].unique():
                aulas_professor = (
                    self.df_class[
                        (self.df_class["teacher"] == professor)
                        & (self.df_class["dias da semana"] == diasemana)
                    ][["nome grupo", "horario"]]
                    .drop_duplicates()
                    .copy()
                )

                if len(aulas_professor) < 2:
                    continue

                aulas_professor["horario_tratado"] = pd.to_datetime(
                    aulas_professor["horario"], format="%H:%M:%S"
                )
                aulas_professor = aulas_professor.sort_values("horario_tratado").reset_index(
                    drop=True
                )

                conflitos = []
                for idx, aula_1 in aulas_professor.iterrows():
                    for idx_2 in range(idx + 1, len(aulas_professor)):
                        aula_2 = aulas_professor.iloc[idx_2]

                        if aula_1["nome grupo"] == aula_2["nome grupo"]:
                            continue

                        diff = aula_2["horario_tratado"] - aula_1["horario_tratado"]
                        if diff > gap:
                            break

                        if diff > pd.Timedelta(minutes=0):
                            conflitos.append((aula_1["nome grupo"], aula_2["nome grupo"]))

                if conflitos:
                    self.result.add(
                        "gap_conflict",
                        (
                            f"Professor {professor} tem turmas com intervalo de até "
                            f"{MIN_GAP_MINUTES} minutos no dia da semana {diasemana}: {conflitos}"
                        ),
                    )

    def check_multiple_classes(self):
        for professor in self.teacher_alocated:
            for diasemana in self.df_class[self.df_class["teacher"] == professor][
                "dias da semana"
            ].unique():
                for horario in self.df_class[self.df_class["teacher"] == professor][
                    "horario"
                ].unique():
                    turmas = self.df_class[
                        (self.df_class["teacher"] == professor)
                        & (self.df_class["dias da semana"] == diasemana)
                        & (self.df_class["horario"] == horario)
                    ]["nome grupo"].unique()
                    if len(turmas) > 1:
                        self.result.add(
                            "same_slot",
                            f"Professor {professor} possui turmas no mesmo horario: {turmas}",
                        )

    def check_modality_group(self):
        modalidades = self.df_class[self.df_class["modalidade"] != "Inglês"]["modalidade"].unique()
        grupo = self.df_class["grupo"].unique()

        colunas_prof = self.df_teach.columns
        diff_mod = set(modalidades) - set(colunas_prof)
        diff_grupo = set(grupo) - set(colunas_prof)
        aulas_mod = self.df_class[self.df_class["modalidade"].isin(diff_mod)]["nome grupo"].unique()
        aulas_grupo = self.df_class[self.df_class["grupo"].isin(diff_grupo)]["nome grupo"].unique()
        if diff_mod:
            self.result.add(
                "missing_modality_column",
                f"Modalidade nao encontrada na tabela de professores: {diff_mod} "
                f"para a seguintes turmas: {aulas_mod}",
            )
        if diff_grupo:
            self.result.add(
                "missing_group_column",
                f"Grupos nao encontrado na tabela de professores: {diff_grupo} "
                f"para a seguintes turmas: {aulas_grupo}",
            )

        for i in self.teacher_alocated:
            if i in self.df_teach["TEACHER"].unique():
                mod = self.df_class[self.df_class["teacher"] == i]["modalidade"].unique()
                for m in mod:
                    if m != "Inglês" and m in self.df_teach.columns:
                        if self.df_teach[self.df_teach["TEACHER"] == i][m].values[0] == 0:
                            self.result.add(
                                "modality_capability",
                                f"Professor {i} nao pode dar aula na modalidade: {m}",
                            )

    def check_teach_status(self):
        for i in self.teacher_alocated:
            if i in self.df_teach["TEACHER"].unique():
                status = self.df_class[self.df_class["teacher"] == i]["status"].unique()
                for s in status:
                    if (
                        s in self.df_teach.columns
                        and self.df_teach[self.df_teach["TEACHER"] == i][s].values[0] == 0
                    ):
                        self.result.add(
                            "status_capability",
                            f"Professor {i} nao pode dar aula no status: {s}",
                        )

    def check_days_of_week(self):
        diff = set(self.df_class["dias da semana"].unique()) - set(DAYS_OF_WEEK)
        if diff:
            classes = self.df_class[self.df_class["dias da semana"].isin(diff)][
                "nome grupo"
            ].unique()
            self.result.add(
                "invalid_day",
                f"Dia da semana nao está certo :{diff} para a turma : {classes}",
            )

    def check_stage(self):
        estagio_list = self.df_class.loc[
            ~(self.df_class["stage"].str.contains("ESTAGIO|MBA|CONV", na=False))
        ]["stage"].unique()
        turmas_list = self.df_class.loc[
            ~(self.df_class["stage"].str.contains("ESTAGIO|MBA|CONV", na=False))
        ]["nome grupo"].unique()
        if len(estagio_list) > 0:
            self.result.add(
                "invalid_stage",
                f"ESTAGIO com problema: {estagio_list} para os estagios: {turmas_list}",
            )

        for i in self.teacher_alocated:
            stage = self.df_class.loc[
                (
                    (self.df_class["stage"].str.contains("ESTAGIO", na=False))
                    & (self.df_class["teacher"] == i)
                    & (self.df_class["modalidade"] != "Espanhol")
                )
            ]["stage"].unique()
            if i in self.df_teach["TEACHER"].values:
                for s in stage:
                    if s not in self.df_teach.columns:
                        continue
                    if self.df_teach[self.df_teach["TEACHER"] == i][s].values[0] == 0:
                        self.result.add(
                            "stage_capability",
                            f"Professor {i} nao pode dar aula no estagio: {s}",
                        )

    def check_sequence_classes(self):
        meio_dia = pd.to_datetime("12:00").time()

        for professor in self.teacher_alocated:
            for diasemana in self.df_class[self.df_class["teacher"] == professor][
                "dias da semana"
            ].unique():
                if diasemana == SATURDAY:
                    continue  # Saturday ignores unidade adjacency rules

                df_prof = self.df_class[
                    (self.df_class["teacher"] == professor)
                    & (self.df_class["dias da semana"] == diasemana)
                    & (self.df_class["status"] == "PRESENCIAL")
                ].sort_values(by="horario_tratado")

                if len(df_prof) < 2:
                    continue

                df_manha = df_prof[df_prof["horario_tratado"].dt.time <= meio_dia]
                df_tarde = df_prof[df_prof["horario_tratado"].dt.time > meio_dia]

                unidades_manha = df_manha["unidade"].unique()
                unidades_tarde = df_tarde["unidade"].unique()
                if len(unidades_manha) > 1:
                    turmas = df_manha["nome grupo"].tolist()
                    self.result.add(
                        "unit_sequence_morning",
                        (
                            f"Conflito Manhã: Professor {professor} nos dias {diasemana}. "
                            f"tem aulas em unidades diferentes {unidades_manha.tolist()}. "
                            f"Turmas: {turmas}"
                        ),
                    )

                if len(unidades_tarde) > 1:
                    turmas = df_tarde["nome grupo"].tolist()
                    self.result.add(
                        "unit_sequence_afternoon",
                        (
                            f"Conflito Tarde: Professor {professor} nos dias {diasemana}. "
                            f"tem aulas em unidades diferentes {unidades_tarde.tolist()}. "
                            f"Turmas: {turmas}"
                        ),
                    )

    def validator_min_classes(self):
        if "TEACHER" not in self.df_teach.columns or "MEDIA" not in self.df_teach.columns:
            raise ValueError("DataFrame de professores precisa das colunas 'TEACHER' e 'MEDIA'")

        if "teacher" not in self.df_class.columns or "n aulas" not in self.df_class.columns:
            raise ValueError("DataFrame de aulas precisa das colunas 'teacher' e 'n aulas'")

        aulas_prealocadas = self.df_class[
            (self.df_class["teacher"].notnull())
            & (self.df_class["teacher"].astype(str).str.strip() != "-")
            & (self.df_class["teacher"].astype(str).str.strip().str.lower() != "nan")
        ].drop_duplicates(subset=["teacher", "nome grupo"])
        carga_professores = aulas_prealocadas.groupby("teacher")["n aulas"].sum()

        for _, professor_info in self.df_teach.iterrows():
            nome = professor_info["TEACHER"]
            media = professor_info["MEDIA"]
            maximo = media

            aulas_alocadas = carga_professores.get(nome, 0)

            if aulas_alocadas > maximo:
                excesso = aulas_alocadas - maximo
                self.result.add(
                    "over_media",
                    (
                        f"PROFESSOR PRÉ-ALOCADO ACIMA DA MÉDIA: {nome} | "
                        f"Aulas pré-alocadas: {aulas_alocadas} | "
                        f"Máximo: {maximo} | "
                        f"Excesso: {excesso} aula(s)"
                    ),
                    severity="warning",
                )

    def check_restrictions_teacher(self):
        df_restricoes = self.df_class[
            (self.df_class["teacher"].notnull())
            & (self.df_class["teacher"].astype(str).str.strip() != "-")
            & (self.df_class["restricoes_professor"].notnull())
        ]

        for _, aula in df_restricoes.iterrows():
            professor = aula["teacher"]
            restricoes = [
                item.strip()
                for item in str(aula["restricoes_professor"]).split(",")
                if item.strip()
            ]
            if professor in restricoes:
                self.result.add(
                    "restriction_violation",
                    (
                        f"Professor {professor} está pré-alocado na turma "
                        f"{aula['nome grupo']}, mas aparece em restricoes_professor."
                    ),
                )

    def check_unidade(self):
        for i in self.teacher_alocated:
            if i in self.df_teach["TEACHER"].unique():
                unidade = self.df_class[
                    (self.df_class["teacher"] == i)
                    & (self.df_class["status"] == "PRESENCIAL")
                    & (self.df_class["dias da semana"] != SATURDAY)
                ]["unidade"].unique()
                for uni in unidade:
                    col = str(uni).upper()
                    if col not in self.df_teach.columns:
                        continue
                    if self.df_teach[self.df_teach["TEACHER"] == i][col].values[0] == 0:
                        self.result.add(
                            "unit_capability",
                            f"Professor {i} nao pode dar aula na unidade: {uni}",
                        )

    def check_teacher_class_type(self):
        for i in self.teacher_alocated:
            if i in self.df_teach["TEACHER"].unique():
                class_type = self.df_class[self.df_class["teacher"] == i]["grupo"].unique()
                for ct in class_type:
                    if ct not in self.df_teach.columns:
                        continue
                    if self.df_teach[self.df_teach["TEACHER"] == i][ct].values[0] == 0:
                        self.result.add(
                            "group_type_capability",
                            f"Professor {i} nao pode dar aula no tipo de aula: {ct}",
                        )


# Backward-compatible lowercase alias
validador = Validator
