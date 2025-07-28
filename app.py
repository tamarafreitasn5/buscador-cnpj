import streamlit as st
import pandas as pd
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# --- CONFIGURAÇÕES ---
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# --- TÍTULO ---
st.title("Leitor de arquivos do Google Drive")

# --- AUTENTICAÇÃO USANDO OS SECRETS DO STREAMLIT ---
service_account_info = json.loads(st.secrets["google_service_account"].to_json())
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)

# --- CONSTRUÇÃO DO SERVIÇO DRIVE ---
drive_service = build("drive", "v3", credentials=creds)

# --- ID DA PASTA DO DRIVE (pode mudar para o que precisar) ---
FOLDER_ID = "COLE_AQUI_O_ID_DA_PASTA_DO_DRIVE"

# --- FUNÇÃO PARA BUSCAR OS ARQUIVOS DENTRO DA PASTA ---
def listar_arquivos(folder_id):
    query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet'"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    return results.get("files", [])

# --- LISTA OS ARQUIVOS E MOSTRA NA INTERFACE ---
arquivos = listar_arquivos(FOLDER_ID)
nomes = [arq["name"] for arq in arquivos]
ids = [arq["id"] for arq in arquivos]

if arquivos:
    escolha = st.selectbox("Selecione um arquivo", nomes)
    arquivo_id = ids[nomes.index(escolha)]
    link = f"https://docs.google.com/spreadsheets/d/{arquivo_id}/edit"
    st.markdown(f"[Abrir no Google Sheets]({link})")
else:
    st.warning("Nenhum arquivo encontrado na pasta.")
