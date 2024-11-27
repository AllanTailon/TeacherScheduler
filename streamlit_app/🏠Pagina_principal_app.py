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

file_path = Path("streamlit_app/Authenticator/hashed_pw.pkl")
with file_path.open("rb") as file:
    hashed_passwords = pickle.load(file)

with open('streamlit_app/Authenticator/config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

authenticator.login()

if st.session_state["authentication_status"] is False:
    st.error("Usuário/Senha está incorreta")

elif st.session_state["authentication_status"] == None:
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
elif st.session_state["authentication_status"]:
    
    
    
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
        st.session_state.selected_page = "🏠 Página Principal"

    if st.sidebar.button("🏠 Página Principal"):
        st.session_state.selected_page = "🏠 Página Principal"

    if st.sidebar.button("👨‍🏫 Dashboard de Professores"):
        st.session_state.selected_page = "👨‍🏫 Dashboard de Professores"

    if st.sidebar.button("⏰ Tabela de Disponibilidade"):
        st.session_state.selected_page = "⏰ Tabela de Disponibilidade"

    if st.sidebar.button("📅 Planejador de rota"):
        st.session_state.selected_page = "📅 Planejador de rota"

    if st.sidebar.button("📞 Contate-nos"):
        st.session_state.selected_page = "📞 Contate-nos"

    # Primeira Página
    if st.session_state.selected_page == "🏠 Página Principal":
        def page_home():
            st.markdown("Welcome to Teacher Scheduler!")

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

        st.title("🏠 Welcome to Teacher Scheduler!")

        st.subheader("📖 Manual de Utilização:")

        st.markdown(
            """
        📊 Coleta de Informações
        No início, utilizamos um website chamado Streamlit, onde foi desenvolvido um serviço para coletar informações destinadas a um dashboard de disponibilidade de horários. Essas informações serão armazenadas em um arquivo Excel, que pode ser carregado diretamente através do site.

        ⏰ Tabela de Disponibilidade
        Com base nas informações coletadas, é gerada uma tabela de disponibilidade contendo as condições especificadas. Essa tabela pode ser exportada como um relatório no formato Excel.

        📅 Planejador de Rotas
        O projeto final consiste em um planejador de rotas, que utiliza todas as informações coletadas para alocar os professores em suas respectivas turmas, considerando as condições específicas de cada um. O resultado também pode ser exportado como um relatório no formato Excel.

        📞 Adicional: Abertura de Chamados
        O sistema conta com a funcionalidade adicional de abertura de chamados para solicitar ajuda, caso necessário.
        """
        )
        
        login_image_path = "streamlit_app/images/diagram.png"
        login_image = load_image(login_image_path)

        st.markdown(
            f"""
            <div style="text-align: center;">
                <img src="data:image/png;base64,{login_image}" width="800">
            </div>
            """,
            unsafe_allow_html=True
        )


    # Segunda Página
    elif st.session_state.selected_page == "👨‍🏫 Dashboard de Professores":
        st.header("👨‍🏫 Dashboard de Disponibilidade")

        def carregar_dados():
            colunas = ['Professor', 'Satélite', 'Vicentina', 'Jardim', 'Online', 
                    'Manhã', 'Tarde', 'Noite', 'Sábado', 'Notebook', 'Computador',
                    'Carro', 'Moto', 'Ingles', 'Espanhol', 'VIP', 'CONV',
                    'In-Company', 'Kids', 'Data']
            try:
                if os.path.exists("disponibilidade.csv"):
                    df = pd.read_csv("disponibilidade.csv")
                    if df.empty:
                        return pd.DataFrame(columns=colunas)
                    df = df[colunas]
                    return df.fillna(0)
            except Exception as e:
                print(f"Erro ao ler o arquivo: {e}")
                return pd.DataFrame(columns=colunas)

        def deletar_linha(index):
            st.session_state.df_disponibilidade.drop(index, inplace=True)
            st.session_state.df_disponibilidade.reset_index(drop=True, inplace=True)
            st.session_state.df_disponibilidade.to_csv("disponibilidade.csv", index=False)

        if 'df_disponibilidade' not in st.session_state:
            st.session_state.df_disponibilidade = carregar_dados()

        nomes_iniciais = ['Professor A']

        if 'disponibilidade' not in st.session_state:
            st.session_state.disponibilidade = {nome: {} for nome in nomes_iniciais}

        st.subheader("Tabela de Disponibilidade:")

        cols1 = st.columns([1, 1, 1, 1])
        with cols1[0]:
            nome_professor = st.text_input("Nome do professor", placeholder="Digite o nome", key="nome")

        with cols1[1]:
            unidades = st.multiselect(
                "Unidades",
                options=['Satélite', 'Vicentina', 'Jardim', 'Online'],
                key="uni"
            )

        with cols1[2]:
            transporte = st.multiselect(
                "Transporte",
                options=['Carro', 'Moto'],
                key="tran"
            )

        with cols1[3]:
            componente = st.multiselect(
                "Máquina",
                options=['Notebook', 'Computador'],
                key="comp"
            )

        cols2 = st.columns([1, 1, 1, 1])
        with cols2[0]:
            disponibilidade = st.multiselect(
                "Disponibilidade",
                options=['Manhã', 'Tarde', 'Noite', 'Sábado'],
                key="disp"
            )
        with cols2[1]:
            modulos = st.multiselect(
                "Módulo",
                options=[f"stage {i}" for i in range(1, 13)],
                key="mod"
            )

        with cols2[2]:
            idiomas = st.multiselect(
                "Idioma",
                options=['Ingles', 'Espanhol'],
                key="idioma"
            )

        with cols2[3]:
            categoria = st.multiselect(
                "Categoria",
                options=['VIP', 'CONV', 'In-Company', 'Kids'],
                key="cat"
            )

        if st.button("Salvar"):
            unidades_bin = {
                'Satélite': 1 if 'Satélite' in unidades else 0,
                'Vicentina': 1 if 'Vicentina' in unidades else 0,
                'Jardim': 1 if 'Jardim' in unidades else 0,
                'Online': 1 if 'Online' in unidades else 0,
            }

            transporte_bin = {
                'Carro': 1 if 'Carro' in transporte else 0,
                'Moto': 1 if 'Moto' in transporte else 0,
            }

            disponibilidade_bin = {
                'Manhã': 1 if 'Manhã' in disponibilidade else 0,
                'Tarde': 1 if 'Tarde' in disponibilidade else 0,
                'Noite': 1 if 'Noite' in disponibilidade else 0,
                'Sábado': 1 if 'Sábado' in disponibilidade else 0,
            }

            maquinas_bin = {
                'Notebook': 1 if 'Notebook' in componente else 0,
                'Computador': 1 if 'Computador' in componente else 0,
            }

            idiomas_bin = {
                'Ingles': 1 if 'Ingles' in idiomas else 0,
                'Espanhol': 1 if 'Espanhol' in idiomas else 0,
            }

            categoria_bin = {
                'VIP': 1 if 'VIP' in categoria else 0,
                'CONV': 1 if 'CONV' in categoria else 0,
                'In-Company': 1 if 'In-Company' in categoria else 0,
                'Kids': 1 if 'Kids' in categoria else 0,
            }

            row_df = pd.DataFrame({
                'Professor': [nome_professor],
                **unidades_bin,
                **transporte_bin,
                **disponibilidade_bin,
                **maquinas_bin,
                **idiomas_bin,
                **categoria_bin,
                'Data': [datetime.now()]
            })

            if st.session_state.df_disponibilidade.empty:
                st.session_state.df_disponibilidade = row_df
            else:
                st.session_state.df_disponibilidade = pd.concat([st.session_state.df_disponibilidade, row_df], ignore_index=True)

            st.session_state.df_disponibilidade.to_csv("disponibilidade.csv", index=False)
            st.success("Dados salvos com sucesso!")

    # Terceira Página
    elif st.session_state.selected_page == "⏰ Tabela de Disponibilidade":
        st.header("⏰ Tabela de Disponibilidade")

        def deletar_linha(linha):
            st.session_state.df_disponibilidade.drop(linha,inplace=True).reset_index(drop=True, inplace=True)

        if 'df_disponibilidade' in st.session_state:
            st.dataframe(st.session_state.df_disponibilidade)
        
        if st.button("Gerar mock de professores"):
            st.session_state['info_professors'] = mock_teach_df(50)
            st.dataframe(st.session_state['info_professors'])

            st.markdown(
                """
                <style>
                .stSelectbox > div[data-baseweb="select"] {
                    width: 200px;  /* Ajuste o valor conforme necessário */
                }
                </style>
                """,
                unsafe_allow_html=True
            )

            linha_disponivel = st.selectbox("Selecione a linha a ser deletada:", st.session_state.df_disponibilidade.index)

            if st.button("Deletar linha"):
                deletar_linha(linha_disponivel)

        st.subheader("Exportar Dados para Excel")
        if st.button("Exportar para Excel"):
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                st.session_state.df_disponibilidade.to_excel(writer, index=False, sheet_name='Disponibilidade')
            buffer.seek(0)

            st.download_button(
                label="Baixar Excel",
                data=buffer,
                file_name="DISPONIBILIDADE_PROFESSORES.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    # Quarta Página
    elif st.session_state.selected_page == "📅 Planejador de rota":
        st.header("📅 Planejador de rota")

        uploaded_file = st.file_uploader(
            "Upload do arquivo das turmas", type=["xlsx"]
        )

        if uploaded_file:
            aulas_raw = pd.read_excel(uploaded_file,header=1)
            st.dataframe(aulas_raw)

            if st.button("Gerar Rotas"):

                if 'info_professors' not in st.session_state:
                    st.error("Por favor, insira os dados dos professores primeiro.")

                else:
                    aulas_simples, doub, tri = base_selection(aulas_raw)
                    
                    aulas_duplicadas = expand_rows(doub, lambda row: replicate_row(row, times=2))
                    aulas_triplicadas = expand_rows(tri, lambda row: replicate_row(row, times=3))
                    
                    df_tratado = pd.concat([aulas_simples, aulas_duplicadas, aulas_triplicadas], ignore_index=True)
                    df_final = clean_data(df_tratado)
                    
                    Ts = TeacherScheduler(df_final, st.session_state['info_professors'])
                    base_alocada = Ts.schedule_teachers()

                    st.write("Rotas Geradas!")
                    st.dataframe(base_alocada)

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
            st.warning("Por favor, faça o upload do arquivo das turmas.")

    # Quinta Página
    elif st.session_state.selected_page == "📞 Contate-nos":
        st.header("📞 Abra um chamado")

        contact_form = """
        <form action="https://formsubmit.co/teacher.scheduler.contact@gmail.com" method="POST">
            <input type="hidden" name="_captcha" value="false">
            <input type="text" name="name" placeholder="Digite seu nome" required>
            <input type="email" name="email" placeholder="Digite seu e-mail" required>
            <textarea name="message" placeholder="Digite sua mensagem"></textarea>
            <button type="submit">Send</button>
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
