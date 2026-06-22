FROM python:3.9-bullseye

WORKDIR /app

COPY . .

RUN pip3 install -r requirements.txt

EXPOSE 8501

ENTRYPOINT ["streamlit", "run"]

CMD ["Pagina_principal_app.py"]