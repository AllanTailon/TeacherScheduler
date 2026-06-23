import pickle
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st
import streamlit_authenticator as stauth
import base64
import os
import io
from utils import (
    load_rota_excel,
    export_rota_excel,
    build_rota_titulo,
    parse_rota_titulo,
    parse_dd_mm_to_date,
    transform_classes_dateframe,
    transform_teacher_dataframe,
    transform_alocation_dataframe,
    enviar_email_para_todos,
)
from teacher_alocation import TeacherScheduler
from validador import validador
import json

st.set_page_config(
    page_title="Teacher Scheduler",
    page_icon="🧑‍🏫",
    layout="centered"
)

def load_image(image_file):
    with open(image_file, "rb") as image:
        return base64.b64encode(image.read()).decode()

image_path = "streamlit_app/images/thefamilyidiomas.jpg"
background_image = load_image(image_path)

names = ["admin", "Luiza Bindel", "Henrique Marcondes"]
usernames = ["admin", "LuizaB", "HenriqueM"]

cookie_name = "Teacher Scheduler"
key = "abcdef"

file_path = Path("streamlit_app/Authenticator/hashed_pw.pkl")
with file_path.open("rb") as file:
    hashed_passwords = pickle.load(file)

authenticator = stauth.Authenticate(
    names, usernames, hashed_passwords, cookie_name, key, cookie_expiry_days=30
)

name, authentication_status, username = authenticator.login("Login", "main")

if authentication_status == False:
    st.error("Usuário/Senha está incorreta")
elif authentication_status == None:
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url(data:image/png;base64,{background_image});
            background-size: 29%;
            background-position: 25% top-center;
            background-repeat: no-repeat;
            height: 80vh;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
elif authentication_status:
    
    
    
    def page_home():

        st.markdown(
        """
        <style>
        .stApp {
            background-image: none;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


    left_column, right_column = st.columns(2)

    hide_st_style = """
                <style>
                #MainMenu {visibility: hidden;}
                footer {visibility: hidden;}
                header {visibility: hidden;}
                </style>
                """
    st.markdown(hide_st_style, unsafe_allow_html=True)


    st.sidebar.title(
        f"Bem-vindo!"
    )
    st.sidebar.markdown("---")

    if 'selected_page' not in st.session_state:
        st.session_state.selected_page = "📅 Planejador de Rota"

    if st.sidebar.button("📅 Planejador de rota"):
        st.session_state.selected_page = "📅 Planejador de Rota"

    if st.sidebar.button("📧 Enviar Rota"):
        st.session_state.selected_page = "📧 Enviar Rota"

    if st.sidebar.button("🔄️ Substituições"):
        st.session_state.selected_page = "🔄️ Substituições"


    # Primeira Página
    if st.session_state.selected_page == "📅 Planejador de Rota":
        st.header("📅 Planejador de rota")

        st.subheader("Upload do arquivo da Rota")
        rota_uploaded_file = st.file_uploader("Faça o upload do arquivo da Rota", type=["xlsx"], key="rota_uploader")

        if rota_uploaded_file:
            rota_bytes = rota_uploaded_file.getvalue()
            st.session_state['rota_template_bytes'] = rota_bytes
            aulas_raw, rota_titulo, rota_sheet_name = load_rota_excel(io.BytesIO(rota_bytes))
            st.session_state['rota_sheet_name'] = rota_sheet_name
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
            professores_uploaded_file = st.file_uploader("Faça o upload do arquivo dos Professores", type=["xlsx"], key="professores_uploader")

            if professores_uploaded_file:
                professores_raw = transform_teacher_dataframe(pd.read_excel(professores_uploaded_file))
                st.dataframe(professores_raw)

                if st.button("Verificar Dados"):
                     with st.spinner(text="Validando Dados..."):
                        
                        classes_result = transform_classes_dateframe(aulas_raw)
                        professores_result = professores_raw
                        Validador = validador(classes_result, professores_result)
                        Validador.check_problem()
                        st.success("Feito!")
                         
                if st.button("Gerar Rotas"):
                    
                    with st.spinner(text="Gerando Rotas..."):

                        classes_result = transform_classes_dateframe(aulas_raw)
                        professores_result = professores_raw

                        Ts = TeacherScheduler(classes_result, professores_result)

                        base_alocada = Ts.schedule_teachers(use_soft_constrait=0)

                        if base_alocada.shape[0] == 0:

                            st.error("Não foi possível gerar a alocação usando condições altas. Utilizando condição medias.")
                        
                            base_alocada = Ts.schedule_teachers(use_soft_constrait=1)
                        
                            if base_alocada.shape[0] == 0:

                                st.error("Não foi possível gerar a alocação usando condições medias. Utilizando condição baixas.")
                                
                                base_alocada = Ts.schedule_teachers(use_soft_constrait=2)
                        

                        df_results,aulas_nao_alocadas = transform_alocation_dataframe(aulas_raw,base_alocada)

                    st.success("Feito!")
                    st.dataframe(df_results)

                    st.subheader("Aulas não alocadas")
                    st.dataframe(aulas_nao_alocadas)
                    
                    processed_file = export_rota_excel(
                        df_results,
                        titulo=rota_titulo_export,
                        template_bytes=st.session_state.get('rota_template_bytes'),
                        sheet_name=st.session_state.get('rota_sheet_name'),
                    )

                    st.download_button(
                        label="Download das Rotas",
                        data=processed_file,
                        file_name="rotas_geradas.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        else:
            st.warning("Por favor, faça o upload do arquivo da Rota primeiro.")


    # Página de envio de email
    elif st.session_state.selected_page == "📧 Enviar Rota":
        st.header("📧 Enviar Rota por e-mail")

        LOG_FILE = "logs_temp.json"  # Arquivo temporário para armazenar os logs

        def load_logs():
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            return []

        def save_logs(log_messages):
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                json.dump(log_messages, f, indent=4)

        if "log_messages" not in st.session_state:
            st.session_state.log_messages = load_logs()

        rota_uploaded_file = st.file_uploader("Faça o upload do arquivo da Rota gerada", type=["xlsx"], key="rota_uploader")

        st._main.markdown("---")

        emails_uploaded_file = st.file_uploader("Faça o upload do arquivo da Base de Professores", type=["xlsx"], key="emails_uploader_2")

        if rota_uploaded_file and emails_uploaded_file:
            rota_bytes = rota_uploaded_file.getvalue()
            rotas_df, _, _ = load_rota_excel(io.BytesIO(rota_bytes))
            emails_df = pd.read_excel(emails_uploaded_file)

            rotas_df.rename(columns={'teacher': 'Teacher', 'nome grupo': 'Nome Grupo'}, inplace=True)
            emails_df.rename(columns={'TEACHER': 'Teacher'}, inplace=True)

            if 'Teacher' in rotas_df.columns and 'Teacher' in emails_df.columns and 'Nome Grupo' in rotas_df.columns:
                combined_df = pd.merge(rotas_df, emails_df, on="Teacher", how="left")

                if st.button("📧 Enviar e-mail para os professores"):
                    with st.spinner("Enviando e-mails..."):
                        new_logs = enviar_email_para_todos(combined_df, rota_bytes)
                        st.session_state.log_messages.extend(new_logs)
                        save_logs(st.session_state.log_messages)

                    st.success("Processo de envio finalizado!")

        if st.session_state.log_messages:
            st.subheader("📜 Logs de Envios")
            st.code("\n".join(st.session_state.log_messages), language="plaintext")

            if st.button("🗑️ Deletar Logs"):
                st.session_state.log_messages = []
                if os.path.exists(LOG_FILE):
                    os.remove(LOG_FILE)
                st.rerun()


    st.sidebar.markdown("---")

    authenticator.logout("Logout", "sidebar")