import pickle
from pathlib import Path

import streamlit_authenticator as stauth

names = ["Carlos Ivanski", "Allan Tailon"]
usernames = ["c_ivanski", "a_tailon"]
passwords = ["XXX", "XXX"]

hashed_passwords = stauth.Hasher(passwords).generate()

file_path = Path(__file__).parent / "hashed_pw.pkl"
with file_path.open("wb") as file:
    pickle.dump(hashed_passwords, file)