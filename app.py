import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# --- CONFIGURAÇÕES ---
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# --- TÍTULO ---
st.title("Leitor de arquivos do Google Drive")

# --- AUTENTICAÇÃO USANDO OS SECRETS DO STREAMLIT ---
service_account_info = st.secrets["google_service_account"]
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)

# --- ID DA PASTA DO DRIVE ---
FOLDER_ID = "19LsEdkxcp-PfdpL5ZE-PA257u51umlld"

# --- FUNÇÃO PARA BUSCAR OS ARQUIVOS DENTRO DA PASTA ---
def listar_arquivos(folder_id):
    query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet'"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    return results.get("files", [])

# --- CONSTRUÇÃO DO SERVIÇO DRIVE ---
drive_service = build("drive", "v3", credentials=creds)

# --- LISTA OS ARQUIVOS E MOSTRA NA INTERFACE ---
arquivos = listar_arquivos(FOLDER_ID)

if arquivos:
    nomes = [arq["name"] for arq in arquivos]
    ids = [arq["id"] for arq in arquivos]
    escolha = st.selectbox("Selecione um arquivo", nomes)
    arquivo_id = ids[nomes.index(escolha)]
    link = f"https://docs.google.com/spreadsheets/d/{arquivo_id}/edit"
    st.markdown(f"[Abrir no Google Sheets]({link})")
else:
    st.warning("Nenhum arquivo encontrado na pasta.")
