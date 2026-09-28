"""Teacher Scheduler — Streamlit entrypoint (no login)."""

from __future__ import annotations

import io
import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from config import app_dir
from constants import SOFT_LEVELS
from teacher_allocation import ScheduleResult, TeacherScheduler
from utils import (
    build_rota_titulo,
    enviar_email_para_todos,
    export_rota_excel,
    load_rota_excel,
    parse_dd_mm_to_date,
    parse_rota_titulo,
    transform_allocation_dataframe,
    transform_classes_dataframe,
    transform_teacher_dataframe,
)
from validator import Validator

APP_DIR = app_dir()
LOG_FILE = Path("logs_temp.json")

st.set_page_config(
    page_title="Teacher Scheduler",
    page_icon="🧑‍🏫",
    layout="centered",
)


def render_validation(result) -> None:
    for issue in result.errors:
        st.error(issue.message)
    for issue in result.warnings:
        st.warning(issue.message)
    if result.ok and not result.warnings:
        st.success("Nenhum problema crítico encontrado.")
    elif result.ok:
        st.success("Validação concluída com avisos (geração ainda permitida).")
    else:
        st.error("Corrija os erros críticos antes de gerar as rotas.")


def run_soft_ladder(scheduler: TeacherScheduler) -> ScheduleResult:
    last: ScheduleResult | None = None
    for level in SOFT_LEVELS:
        result = scheduler.schedule_teachers(use_soft_constraint=level)
        last = result
        if result.success:
            return result
    assert last is not None
    return last


hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

st.sidebar.title("Teacher Scheduler")
st.sidebar.markdown("---")

if "selected_page" not in st.session_state:
    st.session_state.selected_page = "📅 Planejador de Rota"

if st.sidebar.button("📅 Planejador de rota"):
    st.session_state.selected_page = "📅 Planejador de Rota"

if st.sidebar.button("📧 Enviar Rota"):
    st.session_state.selected_page = "📧 Enviar Rota"

# Planejador
if st.session_state.selected_page == "📅 Planejador de Rota":
    st.header("📅 Planejador de rota")

    st.subheader("Upload do arquivo da Rota")
    rota_uploaded_file = st.file_uploader(
        "Faça o upload do arquivo da Rota", type=["xlsx"], key="rota_uploader_planner"
    )

    if rota_uploaded_file:
        rota_bytes = rota_uploaded_file.getvalue()
        st.session_state["rota_template_bytes"] = rota_bytes
        aulas_raw, rota_titulo, rota_sheet_name = load_rota_excel(io.BytesIO(rota_bytes))
        st.session_state["rota_sheet_name"] = rota_sheet_name
        st.dataframe(aulas_raw)

        st.subheader("Período da rota")
        inicio_str, fim_str = parse_rota_titulo(rota_titulo)
        hoje = datetime.now().date()
        col_inicio, col_fim = st.columns(2)
        with col_inicio:
            data_inicio = st.date_input(
                "Data início",
                value=parse_dd_mm_to_date(inicio_str) if inicio_str else hoje,
                format="DD/MM/YYYY",
                key="rota_data_inicio",
            )
        with col_fim:
            data_fim = st.date_input(
                "Data fim",
                value=parse_dd_mm_to_date(fim_str) if fim_str else hoje,
                format="DD/MM/YYYY",
                key="rota_data_fim",
            )

        rota_titulo_export = build_rota_titulo(
            data_inicio.strftime("%d/%m"),
            data_fim.strftime("%d/%m"),
        )
        st.caption(f"Título no Excel: **{rota_titulo_export}**")

        st.subheader("Upload do arquivo dos Professores")
        professores_uploaded_file = st.file_uploader(
            "Faça o upload do arquivo dos Professores",
            type=["xlsx"],
            key="professores_uploader",
        )

        if professores_uploaded_file:
            professores_raw = transform_teacher_dataframe(
                pd.read_excel(professores_uploaded_file)
            )
            st.dataframe(professores_raw)

            if st.button("Verificar Dados"):
                with st.spinner(text="Validando Dados..."):
                    classes_result = transform_classes_dataframe(aulas_raw)
                    validation = Validator(classes_result, professores_raw).check_problem()
                    st.session_state["last_validation_ok"] = validation.ok
                    render_validation(validation)

            if st.button("Gerar Rotas"):
                classes_result = transform_classes_dataframe(aulas_raw)
                validation = Validator(classes_result, professores_raw).check_problem()
                render_validation(validation)

                if not validation.ok:
                    st.stop()

                with st.spinner(text="Gerando Rotas..."):
                    scheduler = TeacherScheduler(classes_result, professores_raw)
                    schedule = run_soft_ladder(scheduler)

                    if not schedule.success:
                        st.error(
                            "Não foi possível gerar a alocação com os dados atuais. "
                            "Revise disponibilidade, restrições e turmas pré-preenchidas."
                        )
                        st.stop()

                    df_results, aulas_nao_alocadas = transform_allocation_dataframe(
                        aulas_raw, schedule.allocations
                    )

                st.success("Rotas geradas com sucesso!")
                st.dataframe(df_results)

                st.subheader("Aulas não alocadas")
                st.dataframe(aulas_nao_alocadas)

                processed_file = export_rota_excel(
                    df_results,
                    titulo=rota_titulo_export,
                    template_bytes=st.session_state.get("rota_template_bytes"),
                    sheet_name=st.session_state.get("rota_sheet_name"),
                )

                st.download_button(
                    label="Download das Rotas",
                    data=processed_file,
                    file_name="rotas_geradas.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
    else:
        st.warning("Por favor, faça o upload do arquivo da Rota primeiro.")

elif st.session_state.selected_page == "📧 Enviar Rota":
    st.header("📧 Enviar Rota por e-mail")

    def load_logs():
        if LOG_FILE.exists():
            with LOG_FILE.open("r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def save_logs(log_messages):
        with LOG_FILE.open("w", encoding="utf-8") as f:
            json.dump(log_messages, f, indent=4)

    if "log_messages" not in st.session_state:
        st.session_state.log_messages = load_logs()

    rota_uploaded_file = st.file_uploader(
        "Faça o upload do arquivo da Rota gerada",
        type=["xlsx"],
        key="rota_uploader_email",
    )

    st.markdown("---")

    emails_uploaded_file = st.file_uploader(
        "Faça o upload do arquivo da Base de Professores",
        type=["xlsx"],
        key="emails_uploader_2",
    )

    if rota_uploaded_file and emails_uploaded_file:
        rota_bytes = rota_uploaded_file.getvalue()
        rotas_df, _, _ = load_rota_excel(io.BytesIO(rota_bytes))
        emails_df = pd.read_excel(emails_uploaded_file)

        rotas_df.rename(
            columns={"teacher": "Teacher", "nome grupo": "Nome Grupo"}, inplace=True
        )
        emails_df.rename(columns={"TEACHER": "Teacher"}, inplace=True)

        if (
            "Teacher" in rotas_df.columns
            and "Teacher" in emails_df.columns
            and "Nome Grupo" in rotas_df.columns
        ):
            combined_df = pd.merge(rotas_df, emails_df, on="Teacher", how="left")

            if st.button("📧 Enviar e-mail para os professores"):
                with st.spinner("Enviando e-mails..."):
                    try:
                        new_logs = enviar_email_para_todos(combined_df, rota_bytes)
                    except RuntimeError as exc:
                        st.error(str(exc))
                        new_logs = []
                    st.session_state.log_messages.extend(new_logs)
                    save_logs(st.session_state.log_messages)

                if new_logs:
                    st.success("Processo de envio finalizado!")

    if st.session_state.log_messages:
        st.subheader("📜 Logs de Envios")
        st.code("\n".join(st.session_state.log_messages), language="plaintext")

        if st.button("🗑️ Deletar Logs"):
            st.session_state.log_messages = []
            if LOG_FILE.exists():
                os.remove(LOG_FILE)
            st.rerun()
