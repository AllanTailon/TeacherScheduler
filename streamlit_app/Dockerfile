FROM python:3.9-bullseye

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt

COPY . /app/streamlit_app

EXPOSE 8501

ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["streamlit", "run"]
CMD ["streamlit_app/Pagina_principal_app.py", "--server.address=0.0.0.0", "--server.port=8501"]
