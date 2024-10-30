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

        st.markdown(
            """
            Streamlit is an open-source app framework built specifically for
            Machine Learning and Data Science projects.
            **👈 Select a demo from the sidebar** to see some examples
            of what Streamlit can do!
            ### Want to learn more?
            - Check out [streamlit.io](https://streamlit.io)
            - Jump into our [documentation](https://docs.streamlit.io)
            - Ask a question in our [community
                forums](https://discuss.streamlit.io)
            ### See more complex demos
            - Use a neural net to [analyze the Udacity Self-driving Car Image
                Dataset](https://github.com/streamlit/demo-self-driving)
            - Explore a [New York City rideshare dataset](https://github.com/streamlit/demo-uber-nyc-pickups)
        """
        )

        login_image_path = "streamlit_app/images/gato.jpg"
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
            colunas = ['Professor', 'Unidades', 'Carro', 'Máquinas', 'Disponibilidade', 'Módulo', 'Idioma', 'Categoria', 'Data']
            try:
                if os.path.exists("disponibilidade.csv"):
                    df = pd.read_csv("disponibilidade.csv")
                    if df.empty:
                        return pd.DataFrame(columns=colunas)
                    return df
            except Exception as e:
                print(f"Erro ao ler o arquivo: {e}")

        def deletar_linha(index):
                st.session_state.df_disponibilidade.drop(index,inplace=True).reset_index(drop=True,inplace=True)
                st.session_state.df_disponibilidade.to_csv("disponibilidade.csv")

        if 'df_disponibilidade' not in st.session_state:
            st.session_state.df_disponibilidade = carregar_dados()

        data_modificada_formatada = datetime.now().strftime("%d/%m/%Y")
        st.write(f"Data selecionada: {data_modificada_formatada}")

        nomes_iniciais = ['Professor A']
        unidades = ['Satélite', 'Vicentina', 'Jardim', 'Online']

        if 'disponibilidade' not in st.session_state:
            st.session_state.disponibilidade = {nome: {} for nome in nomes_iniciais}

        st.subheader("Tabela de Disponibilidade:")

        for i, nome_inicial in enumerate(nomes_iniciais):
            cols1 = st.columns([1, 1, 1, 1])
            with cols1[0]:
                nome_professor = st.text_input(f"Nome do professor", nome_inicial, key=f"nome_{i}")

            if nome_professor != nome_inicial:
                st.session_state.disponibilidade[nome_professor] = st.session_state.disponibilidade.pop(nome_inicial, {})

            if nome_professor not in st.session_state.disponibilidade:
                st.session_state.disponibilidade[nome_professor] = {}

            with cols1[1]:
                st.write("Unidades:")
                for unidade in unidades:
                    st.session_state.disponibilidade[nome_professor][unidade] = st.checkbox(f"{unidade}", 
                        value=st.session_state.disponibilidade[nome_professor].get(unidade, False), 
                        key=f"{nome_professor}_{unidade}")

            with cols1[2]:
                st.write("Carro:")
                st.session_state.disponibilidade[nome_professor]['Carro'] = st.checkbox("Tem carro", 
                    value=st.session_state.disponibilidade[nome_professor].get('Carro', False), 
                    key=f"{nome_professor}_carro")

            with cols1[3]:
                st.write("Máquina:")
                maquinas = {}
                with st.container():
                    maquinas['Notebook'] = st.checkbox("Notebook", 
                        value='Notebook' in st.session_state.disponibilidade[nome_professor].get('Máquina', []), 
                        key=f"{nome_professor}_notebook")
                    maquinas['Computador'] = st.checkbox("Computador", 
                        value='Computador' in st.session_state.disponibilidade[nome_professor].get('Máquina', []), 
                        key=f"{nome_professor}_computador")
                    maquinas['NDA'] = st.checkbox("NDA", 
                        value='NDA' in st.session_state.disponibilidade[nome_professor].get('Máquina', []), 
                        key=f"{nome_professor}_nda")
                st.session_state.disponibilidade[nome_professor]['Máquina'] = [key for key, value in maquinas.items() if value]

        cols2 = st.columns([1, 1, 1, 1])
        with cols2[0]:
            st.write("Disponibilidade:")
            periodos = ['Manhã', 'Tarde', 'Noite', 'Sábado']
            disponibilidade_horarios = {}
            with st.container():
                for periodo in periodos:
                    disponibilidade_horarios[periodo] = st.checkbox(periodo, 
                        value=periodo in st.session_state.disponibilidade[nome_professor].get('Disponibilidade', []), 
                        key=f"{nome_professor}_{periodo}")
            st.session_state.disponibilidade[nome_professor]['Disponibilidade'] = [key for key, value in disponibilidade_horarios.items() if value]

        with cols2[1]:
            st.write("Módulos:")
            modulo_opcoes = {}
            with st.container():
                modulo_opcoes['Stage 1'] = st.checkbox("Stage 1", 
                    value='Stage 1' in st.session_state.disponibilidade[nome_professor].get('Modulo', []), 
                    key=f"{nome_professor}_stage1")
                for stage in range(2, 13):  # Stage 2 até Stage 12
                    modulo_opcoes[f'Stage {stage}'] = st.checkbox(f'Stage {stage}', 
                        value=f'Stage {stage}' in st.session_state.disponibilidade[nome_professor].get('Modulo', []), 
                        key=f"{nome_professor}_stage{stage}")
            st.session_state.disponibilidade[nome_professor]['Modulo'] = [key for key, value in modulo_opcoes.items() if value]

        with cols2[2]:
            st.write("Idioma:")
            idioma_opcoes = {}
            with st.container():
                idioma_opcoes['Inglês'] = st.checkbox("Inglês", 
                    value='Inglês' in st.session_state.disponibilidade[nome_professor].get('Idioma', []), 
                    key=f"{nome_professor}_ingles")
                idioma_opcoes['Espanhol'] = st.checkbox("Espanhol", 
                    value='Espanhol' in st.session_state.disponibilidade[nome_professor].get('Idioma', []), 
                    key=f"{nome_professor}_espanhol")
            st.session_state.disponibilidade[nome_professor]['Idioma'] = [key for key, value in idioma_opcoes.items() if value]

        # Nova seção para a coluna "Categoria"
        with cols2[3]:
            st.write("Categoria:")
            categoria_opcoes = ['VIP', 'CONV', 'In-Company', 'Kids']
            for categoria in categoria_opcoes:
                st.session_state.disponibilidade[nome_professor][categoria] = st.checkbox(categoria, 
                    value=categoria in st.session_state.disponibilidade[nome_professor].get('Categoria', []), 
                    key=f"{nome_professor}_{categoria}")

        st.session_state.disponibilidade[nome_professor]['Categoria'] = [key for key, value in st.session_state.disponibilidade[nome_professor].items() if value and key in categoria_opcoes]

        if st.button("Salvar"):
            for nome_professor, dados in st.session_state.disponibilidade.items():
                row_data = {
                    'Professor': nome_professor,
                    'Unidades': ', '.join([unidade for unidade in unidades if dados.get(unidade, False)]),
                    'Carro': 'Sim' if dados.get('Carro', False) else 'Não',
                    'Máquinas': ', '.join(dados.get('Máquina', [])),
                    'Disponibilidade': ', '.join(dados.get('Disponibilidade', [])),
                    'Módulo': ', '.join(dados.get('Modulo', [])),
                    'Idioma': ', '.join(dados.get('Idioma', [])),
                    'Data': data_modificada_formatada,
                    'Categoria': ', '.join(dados.get('Categoria', []))  # Adicionando a nova coluna Categoria
                }
                row_df = pd.DataFrame([row_data])
                st.session_state.df_disponibilidade = pd.concat([st.session_state.df_disponibilidade, row_df], ignore_index=True)

            st.session_state.df_disponibilidade.to_csv("disponibilidade.csv")
            st.success("Dados salvos com sucesso!")

        if False:
            st.subheader("Tabela Atualizada de Disponibilidade:")
            st.dataframe(st.session_state.df_disponibilidade)

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

    # Terceira Página
    elif st.session_state.selected_page == "⏰ Tabela de Disponibilidade":
        st.header("⏰ Tabela de Disponibilidade")

        def deletar_linha(linha):
            st.session_state.df_disponibilidade.drop(linha,inplace=True).reset_index(drop=True, inplace=True)

        if 'df_disponibilidade' in st.session_state:
            st.dataframe(st.session_state.df_disponibilidade)

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

        uploaded_files = st.file_uploader(
            "", accept_multiple_files=True
        )

        for uploaded_file in uploaded_files:
            df = pd.read_excel(uploaded_file)
            
            st.write("filename:", uploaded_file.name)
            
            st.dataframe(df)

        st.subheader("Exportar Dados para Excel")
        
        if st.button("Exportar para Excel"):
            buffer = io.BytesIO()
            
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                st.session_state.df_disponibilidade.to_excel(writer, index=False, sheet_name='Disponibilidade')
            
            buffer.seek(0)
            
            st.download_button(
                label="Baixar Excel",
                data=buffer,
                file_name="SCHEDULER.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


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