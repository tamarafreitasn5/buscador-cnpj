import streamlit as st
import pandas as pd
import os
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from io import BytesIO

# ID da pasta no Google Drive
FOLDER_ID = "1On7gASIN3FhwS9AVowPlpA9Xv7VV7XG1"

# Autenticação com credentials.json
creds = service_account.Credentials.from_service_account_file(
    "credentials.json",
    scopes=["https://www.googleapis.com/auth/drive"]
)
service = build("drive", "v3", credentials=creds)

# Nome original das colunas padronizadas
aliases_colunas = {
    "CNPJ": "CNPJ",
    "Razão Social": "Razão Social",
    "Nome": "Nome",
    "Cargo": "Cargo",
    "E-mail": "E-mail",
    "telefone": "Telefone",
    "celular": "Celular",
    "contatos adicionais/notas": "Notas",
    "Setor/Área": "Setor/Área"
}

def listar_arquivos_na_pasta(folder_id):
    query = f"'{folder_id}' in parents and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    return results.get("files", [])

def baixar_arquivo(file_id):
    request = service.files().get_media(fileId=file_id)
    fh = BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return fh

def normalizar_colunas(df):
    df.columns = [col.strip() for col in df.columns]
    novas_colunas = {}
    for col in df.columns:
        for alias, padrao in aliases_colunas.items():
            if re.search(alias, col, re.IGNORECASE):
                novas_colunas[col] = padrao
    return df.rename(columns=novas_colunas)

@st.cache_data
def carregar_dados():
    arquivos = listar_arquivos_na_pasta(FOLDER_ID)
    todos_dados = []
    
    for arquivo in arquivos:
        nome_arquivo = arquivo["name"]
        file_id = arquivo["id"]
        if nome_arquivo.endswith(".xlsx") or nome_arquivo.endswith(".csv"):
            try:
                conteudo = baixar_arquivo(file_id)
                if nome_arquivo.endswith(".xlsx"):
                    xls = pd.ExcelFile(conteudo)
                    for aba in xls.sheet_names:
                        df = xls.parse(aba)
                        df = normalizar_colunas(df)
                        df["Planilha"] = nome_arquivo
                        df["Aba"] = aba
                        todos_dados.append(df)
                elif nome_arquivo.endswith(".csv"):
                    df = pd.read_csv(conteudo, encoding='utf-8', sep=None, engine='python')
                    df = normalizar_colunas(df)
                    df["Planilha"] = nome_arquivo
                    df["Aba"] = "Arquivo CSV"
                    todos_dados.append(df)
            except Exception as e:
                st.warning(f"Erro ao processar {nome_arquivo}: {e}")
    if todos_dados:
        return pd.concat(todos_dados, ignore_index=True)
    else:
        return pd.DataFrame()

st.set_page_config(page_title="Buscador por CNPJ", page_icon="🔎")
st.title("🔎 Buscador por CNPJ")

cnpj_input = st.text_input("Digite o CNPJ para buscar:")

if cnpj_input:
    cnpj = re.sub(r'\D', '', cnpj_input)  # remove pontuação
    df = carregar_dados()
    if "CNPJ" in df.columns:
        resultados = df[df["CNPJ"].astype(str).str.contains(cnpj)]
        if not resultados.empty:
            colunas_ordenadas = ["CNPJ", "Razão Social", "Nome", "Cargo", "E-mail", "Telefone", "Celular", "Notas", "Setor/Área", "Planilha", "Aba"]
            colunas_disponiveis = [col for col in colunas_ordenadas if col in resultados.columns]
            st.write(resultados[colunas_disponiveis])
        else:
            st.info("Nenhum resultado encontrado para o CNPJ informado.")
    else:
        st.error("Coluna 'CNPJ' não encontrada em nenhuma planilha.")
