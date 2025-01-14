import pickle
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth
from PIL import Image
import base64
import os
from datetime import datetime
import io
from utils import *
from teacher_alocation import TeacherScheduler

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

names = ["Luiza Bindel", "Henrique Marcondes"]
usernames = ["LuizaB", "HenriqueM"]

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

    if st.sidebar.button("📞 Contate-nos"):
        st.session_state.selected_page = "📞 Contate-nos"


    # Primeira Página
    elif st.session_state.selected_page == "📅 Planejador de Rota":
        st.header("📅 Planejador de rota")

        st.subheader("Upload do arquivo da Rota")
        rota_uploaded_file = st.file_uploader("Faça o upload do arquivo da Rota", type=["xlsx"], key="rota_uploader")

        if 'aulas_rotas' not in st.session_state:
            st.session_state['aulas_rotas'] = None

        if st.session_state['aulas_rotas'] is not None:
            st.dataframe(st.session_state['aulas_rotas'])

        if rota_uploaded_file:
            aulas_raw = pd.read_excel(rota_uploaded_file, header=1)
            st.dataframe(aulas_raw)

            st.subheader("Upload do arquivo dos Professores")
            professores_uploaded_file = st.file_uploader("Faça o upload do arquivo dos Professores", type=["xlsx"], key="professores_uploader")

            if professores_uploaded_file:
                professores_raw = pd.read_excel(professores_uploaded_file)
                st.dataframe(professores_raw)

                if st.button("Gerar Rotas"):
                    if 'info_professors' not in st.session_state:
                        st.error("Por favor, insira os dados dos professores primeiro.")
                    else:
                        aulas_simples, doub, tri = base_selection(aulas_raw)

                        aulas_duplicadas = expand_rows(doub, lambda row: replicate_row(row, times=2))
                        aulas_triplicadas = expand_rows(tri, lambda row: replicate_row(row, times=3))

                        df_tratado = pd.concat([aulas_simples, aulas_duplicadas, aulas_triplicadas], ignore_index=True)
                        df_final = clean_data(df_tratado)

                        df_dummie = treat_mock_df(st.session_state['info_professors'], ['Unidades', 'Maquinas', 'disponibilidade', 'Modulo', 'Idiomas', 'Automovel'])
                        Ts = TeacherScheduler(df_final, df_dummie)

                        base_alocada = Ts.schedule_teachers()
                        base_show = pd.merge(aulas_raw, base_alocada, on='Grupo', how='left')

                        st.write("Rotas Geradas!")
                        st.dataframe(base_show[['Professor', 'Grupo', 'Horário', 'Dias da Semana', 'MOD', 'STATUS']])
                        st.session_state['aulas_rotas'] = base_show[['Professor', 'Grupo', 'Horário', 'Dias da Semana', 'MOD', 'STATUS']].copy()

                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine="openpyxl") as writer:
                            df_final.to_excel(writer, index=False, sheet_name="Rotas")
                        processed_file = output.getvalue()

                        st.download_button(
                            label="Download das Rotas",
                            data=processed_file,
                            file_name="rotas_geradas.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
        else:
            st.warning("Por favor, faça o upload do arquivo da Rota primeiro.")


    # Segunda Página
    elif st.session_state.selected_page == "📞 Contate-nos":
        st.header("📞 Abra um chamado")

        contact_form = """
        <form action="https://formsubmit.co/teacher.scheduler.contact@gmail.com" method="POST">
            <input type="hidden" name="_captcha" value="false">
            <input type="text" name="name" placeholder="Digite seu nome" required>
            <input type="email" name="email" placeholder="Digite seu e-mail" required>
            <textarea name="message" placeholder="Digite sua mensagem"></textarea>
            <button type="submit">Enviar</button>
        </form>
        """
        st.markdown(contact_form, unsafe_allow_html=True)

        @st.cache_data
        def load_css():
            file_path = "streamlit_app/style/style.css"
            with open(file_path) as f:
                return f.read()

        try:
            css_content = load_css()
            st.markdown(f'<style>{css_content}</style>', unsafe_allow_html=True)
        except FileNotFoundError:
            st.error("CSS file not found.")

    st.sidebar.markdown("---")

    authenticator.logout("Logout", "sidebar")