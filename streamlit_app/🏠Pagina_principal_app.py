import pickle
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
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

image_path = r"streamlit_app/images/thefamilyidiomas.jpg"
background_image = load_image(image_path)

names = [
    "Bruno Morgillo",
    "Luiza Bindel",
    "Henrique Marcondes"
]

usernames = [
    "Bruno Morgillo",
    "Luiza Bindel",
    "Henrique Marcondes"
]

file_path = Path("streamlit_app/Authenticator/hashed_pw.pkl")
with file_path.open("rb") as file:
    hashed_passwords = pickle.load(file)

authenticator = stauth.Authenticate(
    names,
    usernames,
    hashed_passwords,
    "Teacher Scheduler",
    "abcdef",
    cookie_expiry_days=1
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
        f"Bem-vindo {name}"
    )


    st.sidebar.markdown("---")

    def page_dashboard():
        st.title("👨‍🏫 Dashboard de Professores")
        st.markdown("This is the teachers' dashboard.")

    def page_contact():
        st.title("📞 Contate-nos")
        st.write("Página Teste.")

    if 'selected_page' not in st.session_state:
        st.session_state.selected_page = "🏠 Página Principal"

    if st.sidebar.button("🏠 Página Principal"):
        st.session_state.selected_page = "🏠 Página Principal"
    if st.sidebar.button("👨‍🏫 Dashboard de Professores"):
        st.session_state.selected_page = "👨‍🏫 Dashboard de Professores"
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
            if os.path.exists("disponibilidade.csv"):
                df = pd.read_csv("disponibilidade.csv")
                if df.empty:
                    return pd.DataFrame(columns=['Professor', 'Unidades', 'Carro', 'Máquinas', 'Disponibilidade', 'Módulo', 'Idioma', 'Observações', 'Data'])
                return df
            return pd.DataFrame(columns=['Professor', 'Unidades', 'Carro', 'Máquinas', 'Disponibilidade', 'Módulo', 'Idioma', 'Observações', 'Data'])

        def salvar_dados(df):
            df.to_csv("disponibilidade.csv", index=False)

        def deletar_linha(index):
            if index in st.session_state.df_disponibilidade.index:
                nome_professor = st.session_state.df_disponibilidade.at[index, 'Professor']
                st.session_state.df_disponibilidade = st.session_state.df_disponibilidade.drop(index).reset_index(drop=True)
                salvar_dados(st.session_state.df_disponibilidade)
                st.success(f"Linha do professor '{nome_professor}' deletada com sucesso!")

        if 'df_disponibilidade' not in st.session_state:
            st.session_state.df_disponibilidade = carregar_dados()

        data_modificacao = st.date_input("Data da modificação", value=datetime.today())
        data_modificada_formatada = data_modificacao.strftime("%d/%m/%Y")
        st.write(f"Data selecionada: {data_modificada_formatada}")

        nomes_iniciais = ['Pessoa A']
        unidades = ['Satélite', 'Vicentina', 'Jardim', 'Online']

        if 'disponibilidade' not in st.session_state:
            st.session_state.disponibilidade = {nome: {} for nome in nomes_iniciais}

        st.subheader("Tabela de Disponibilidade:")

        for i, nome_inicial in enumerate(nomes_iniciais):
                cols1 = st.columns([2, 1, 1, 1])
                with cols1[0]:
                    nome_professor = st.text_input(f"Nome do professor", nome_inicial, key=f"nome_{i}")

                if nome_professor != nome_inicial:
                    st.session_state.disponibilidade[nome_professor] = st.session_state.disponibilidade.pop(nome_inicial, {})

                if nome_professor not in st.session_state.disponibilidade:
                    st.session_state.disponibilidade[nome_professor] = {}

                with cols1[1]:
                    st.write("Unidades")
                    for unidade in unidades:
                        st.session_state.disponibilidade[nome_professor][unidade] = st.checkbox(f"{unidade}", 
                            value=st.session_state.disponibilidade[nome_professor].get(unidade, False), 
                            key=f"{nome_professor}_{unidade}")

                with cols1[2]:
                    st.write("Carro")
                    st.session_state.disponibilidade[nome_professor]['Carro'] = st.checkbox("Tem carro", 
                        value=st.session_state.disponibilidade[nome_professor].get('Carro', False), 
                        key=f"{nome_professor}_carro")

                with cols1[3]:
                    st.write("Máquina")
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

                cols2 = st.columns([1, 1, 1, 2])
                with cols2[0]:
                    st.write("Disponibilidade")
                    periodos = ['Manhã', 'Tarde', 'Noite', 'Sábado']
                    disponibilidade_horarios = {}
                    with st.container():
                        for periodo in periodos:
                            disponibilidade_horarios[periodo] = st.checkbox(periodo, 
                                value=periodo in st.session_state.disponibilidade[nome_professor].get('Disponibilidade', []), 
                                key=f"{nome_professor}_{periodo}")
                    st.session_state.disponibilidade[nome_professor]['Disponibilidade'] = [key for key, value in disponibilidade_horarios.items() if value]

                with cols2[1]:
                    st.write("Módulo")
                    modulo_opcoes = {}
                    with st.container():
                        modulo_opcoes['Stage 1'] = st.checkbox("Stage 1", 
                            value='Stage 1' in st.session_state.disponibilidade[nome_professor].get('Modulo', []), 
                            key=f"{nome_professor}_stage1")
                        modulo_opcoes['VIP'] = st.checkbox("VIP", 
                            value='VIP' in st.session_state.disponibilidade[nome_professor].get('Modulo', []), 
                            key=f"{nome_professor}_vip")
                        modulo_opcoes['CONV'] = st.checkbox("CONV", 
                            value='CONV' in st.session_state.disponibilidade[nome_professor].get('Modulo', []), 
                            key=f"{nome_professor}_conv")
                        modulo_opcoes['MBA'] = st.checkbox("MBA", 
                            value='MBA' in st.session_state.disponibilidade[nome_professor].get('Modulo', []), 
                            key=f"{nome_professor}_mba")
                        modulo_opcoes['Kids'] = st.checkbox("Kids", 
                            value='Kids' in st.session_state.disponibilidade[nome_professor].get('Modulo', []), 
                            key=f"{nome_professor}_kids")
                        modulo_opcoes['In-Company'] = st.checkbox("In-Company", 
                            value='In-Company' in st.session_state.disponibilidade[nome_professor].get('Modulo', []), 
                            key=f"{nome_professor}_incompany")
                    st.session_state.disponibilidade[nome_professor]['Modulo'] = [key for key, value in modulo_opcoes.items() if value]

                with cols2[2]:
                    st.write("Idioma")
                    idioma_opcoes = {}
                    with st.container():
                        idioma_opcoes['Inglês'] = st.checkbox("Inglês", 
                            value='Inglês' in st.session_state.disponibilidade[nome_professor].get('Idioma', []), 
                            key=f"{nome_professor}_ingles")
                        idioma_opcoes['Espanhol'] = st.checkbox("Espanhol", 
                            value='Espanhol' in st.session_state.disponibilidade[nome_professor].get('Idioma', []), 
                            key=f"{nome_professor}_espanhol")
                    st.session_state.disponibilidade[nome_professor]['Idioma'] = [key for key, value in idioma_opcoes.items() if value]

                with cols2[3]:
                    st.session_state.disponibilidade[nome_professor]['Observações'] = st.text_area("Observações", 
                        value=st.session_state.disponibilidade[nome_professor].get('Observações', ''), 
                        key=f"{nome_professor}_observacoes")

        def converter_df_para_excel(df):
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, sheet_name='Disponibilidade', index=False)
                writer.save()
            output.seek(0)
            return output

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
                    'Observações': dados.get('Observações', ''),
                    'Data': data_modificada_formatada
                }
                row_df = pd.DataFrame([row_data])
                st.session_state.df_disponibilidade = pd.concat([st.session_state.df_disponibilidade, row_df], ignore_index=True)

            salvar_dados(st.session_state.df_disponibilidade)
            st.success("Dados salvos com sucesso!")

        st.subheader("Tabela Atualizada de Disponibilidade")

        for i, row in st.session_state.df_disponibilidade.iterrows():
                cols = st.columns(len(row) + 1) 
                for j, value in enumerate(row):
                    cols[j].write(value)
                
                if cols[len(row)].button("Deletar", key=f"delete_{i}"):
                    deletar_linha(i)

        st.subheader("Exportar Dados para Excel")
        if st.button("Exportar para Excel"):
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    st.session_state.df_disponibilidade.to_excel(writer, index=False, sheet_name='Disponibilidade')
                buffer.seek(0)
                
                st.download_button(
                    label="Baixar Excel",
                    data=buffer,
                    file_name="PROFESSORES.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
    # Terceira Página
    elif st.session_state.selected_page == "📅 Planejador de rota":
        st.header("📅 Planejador de rota")

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



    # Quarta Página
    elif st.session_state.selected_page == "📞 Contate-nos":
        st.header("📞 Abra um chamado")

        contact_form = """
        <form action="https://formsubmit.co/losbr62@gmail.com" method="POST">
            <input type="hidden" name="_captcha" value="false">
            <input type="text" name="name" placeholder="Digite seu nome" required>
            <input type="email" name="email" placeholder="Digite seu e-mail" required>
            <textarea name="message" placeholder="Digite sua mensagem"></textarea>
            <button type="submit">Send</button>
        </form>
        """

        st.markdown(contact_form, unsafe_allow_html=True)

        def local_css():
            file_path = r"C:\Users\Erione Technologies\Documents\GitHub\TeacherScheduler\streamlit_app\style\style.css"
            with open(file_path) as f:
                st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

        local_css()




    st.sidebar.markdown("---")

    authenticator.logout(button_name="Logout", location="sidebar")