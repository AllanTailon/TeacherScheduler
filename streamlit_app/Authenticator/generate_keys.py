import pickle
from pathlib import Path

import streamlit_authenticator as stauth

names = ["admin", "Luiza Bindel", "Henrique Marcondes"]
usernames = ["admin", "Luiza Bindel", "Henrique Marcondes"]
passwords = ["123456", "123456", "123456"]

hashed_passwords = stauth.Hasher(passwords).generate()

file_path = Path(__file__).parent / "hashed_pw.pkl"
with file_path.open("wb") as file:
    pickle.dump(hashed_passwords, file)