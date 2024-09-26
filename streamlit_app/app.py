import streamlit as st
import pandas as pd
import pickle
from pathlib import Path
import streamlit_authenticator as stauth

st.set_page_config(
    page_title="Teacher Scheduler",
    page_icon="👨‍🏫",
    layout="wide"
)

names = ["Carlos Ivanski", "Allan Tailon"]
usernames = ["c_ivanski", "a_tailon"]

file_path = Path(__file__).parent / "hashed_pw.pkl"
with file_path.open("rb") as file:
    hashed_passwords = pickle.load(file)

authenticator = stauth.Authenticate(names, usernames, hashed_passwords,
    "página_principal", "abcdef", cookie_expiry_days=30)

name, authenticaton_status, username = authenticator.login("Login", "main")

if authenticaton_status == False:
    st.error("Username/Senha está incorreto")

if authenticaton_status == None:
    st.warning("Insira seu Username e Senha")

if authenticaton_status == True:

    st.title("Página Principal")

authenticator.logout("Logout", "sidebar")
st.sidebar.title(f'Bem-vindo {name}')