import streamlit as st
import pandas as pd
import os
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import tempfile
import zipfile

# Nome da pasta no Google Drive
FOLDER_NAME = 'Base teste'

# Autenticação com o Google Drive
def authenticate_gdrive():
    creds_dict = st.secrets["gcp_service_account"]
    credentials = service_account.Credentials.from_service_account_info(creds_dict)
    service = build('drive', 'v3', credentials=credentials)
    return service

# Obtém o ID da pasta pelo nome
def get_folder_id_by_name(folder_name, service):
    results = service.files().list(q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'",
                                   spaces='drive', fields='files(id, name)').execute()
    folders = results.get('files', [])
    if not folders:
        st.error(f"Pasta '{folder_name}' não encontrada.")
        return None
    return folders[0]['id']

# Lista os arquivos dentro da pasta
def list_files_in_folder(folder_id, service):
    query = f"'{folder_id}' in parents and mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'"
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    return results.get('files', [])

# Baixa um arquivo e retorna o caminho temporário
def download_file(file_id, service):
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    temp_file.write(fh.read())
    temp_file.close()
    return temp_file.name

# Padroniza os nomes de colunas
def padronizar_colunas(df):
    df.columns = [str(col).strip() for col in df.columns]
    return df

# Busca dados por CNPJ
def buscar_por_cnpj(cnpj, arquivos):
    resultados = []

    for file_name, file_path in arquivos.items():
        try:
            xls = pd.ExcelFile(file_path)
            for aba in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=aba)
                df = padronizar_colunas(df)
                cnpj_cols = [col for col in df.columns if 'cnpj' in col.lower()]
                if not cnpj_cols:
                    continue
                for col in cnpj_cols:
                    encontrados = df[df[col].astype(str).str.replace(r'\D', '', regex=True) == cnpj]
                    if not encontrados.empty:
                        encontrados['Planilha'] = file_name
                        encontrados['Aba'] = aba
                        resultados.append(encontrados)
        except Exception as e:
            st.warning(f"Erro ao processar {file_name}: {e}")

    if resultados:
        return pd.concat(resultados, ignore_index=True)
    else:
        return pd.DataFrame()

# Interface Streamlit
def main():
    st.title("🔍 Buscador de CNPJ em Planilhas do Google Drive")

    cnpj_input = st.text_input("Digite o CNPJ (apenas números):")
    if not cnpj_input:
        st.stop()

    cnpj_input = re.sub(r'\D', '', cnpj_input)

    service = authenticate_gdrive()
    folder_id = get_folder_id_by_name(FOLDER_NAME, service)
    if not folder_id:
        st.stop()

    files = list_files_in_folder(folder_id, service)
    arquivos = {}
    for file in files:
        file_path = download_file(file['id'], service)
        arquivos[file['name']] = file_path

    resultado = buscar_por_cnpj(cnpj_input, arquivos)

    if not resultado.empty:
        st.success(f"✅ {len(resultado)} resultado(s) encontrado(s).")
        st.dataframe(resultado)
    else:
        st.info("Nenhum resultado encontrado para o CNPJ informado.")

if __name__ == "__main__":
    main()
