FROM python:3.9-bullseye

WORKDIR /root

COPY . .
COPY images/ /root/images

RUN pip3 install -r /root/requirements.txt

EXPOSE 8501

ENTRYPOINT ["streamlit", "run"]

CMD ["Pagina_principal_app.py"]