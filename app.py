import streamlit as st
import pandas as pd
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
import io
from googleapiclient.http import MediaIoBaseDownload

# --- AUTENTICAÇÃO ---
SCOPES = ['https://www.googleapis.com/auth/drive']
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=SCOPES
)
drive_service = build('drive', 'v3', credentials=credentials)

# --- NOME DA PASTA NO DRIVE ---
FOLDER_NAME = 'Base teste'

def get_folder_id_by_name(folder_name):
    results = drive_service.files().list(
        q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'",
        spaces='drive',
        fields='files(id, name)',
    ).execute()
    folders = results.get('files', [])
    if not folders:
        st.error(f'Pasta "{folder_name}" não encontrada.')
        st.stop()
    return folders[0]['id']

def get_spreadsheet_files_from_folder(folder_id):
    query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet'"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    return results.get('files', [])

def read_all_sheets(file_id):
    sheets_service = build('sheets', 'v4', credentials=credentials)
    sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=file_id).execute()
    sheet_names = [sheet['properties']['title'] for sheet in sheet_metadata['sheets']]

    all_data = []
    for sheet_name in sheet_names:
        try:
            sheet = sheets_service.spreadsheets().values().get(
                spreadsheetId=file_id,
                range=sheet_name
            ).execute()
            values = sheet.get('values', [])
            if not values:
                continue
            df = pd.DataFrame(values[1:], columns=values[0])
            df['Planilha'] = file_id
            df['Aba'] = sheet_name
            all_data.append(df)
        except Exception as e:
            st.warning(f"Erro ao ler a aba '{sheet_name}' do arquivo ID {file_id}: {e}")
    return all_data

@st.cache_data(ttl=600)
def load_all_data():
    folder_id = get_folder_id_by_name(FOLDER_NAME)
    files = get_spreadsheet_files_from_folder(folder_id)
    all_dfs = []
    for file in files:
        dfs = read_all_sheets(file['id'])
        for df in dfs:
            df['Planilha'] = file['name']
            all_dfs.append(df)
    return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()

def normalizar_cnpj(cnpj):
    if pd.isna(cnpj):
        return ''
    cnpj = str(cnpj)
    cnpj = re.sub(r'\D', '', cnpj)
    return cnpj.zfill(14)

# --- INTERFACE STREAMLIT ---
st.title("🔎 Buscador de CNPJ nas planilhas do Google Drive")

cnpj_input = st.text_input("Digite o CNPJ para buscar (com ou sem pontuação):")

if cnpj_input:
    cnpj_normalizado = normalizar_cnpj(cnpj_input)
    st.write(f"CNPJ normalizado: `{cnpj_normalizado}`")

    data = load_all_data()
    if 'CNPJ' not in [col.upper() for col in data.columns]:
        st.error("Coluna 'CNPJ' não encontrada nos arquivos.")
        st.stop()

    # Tenta localizar a coluna de CNPJ independentemente do nome exato
    cnpj_col = next((col for col in data.columns if col.strip().upper() == 'CNPJ'), None)
    data['CNPJ_normalizado'] = data[cnpj_col].apply(normalizar_cnpj)

    resultados = data[data['CNPJ_normalizado'] == cnpj_normalizado]

    if not resultados.empty:
        colunas_para_exibir = [
            'CNPJ', 'Razão Social', 'Nome', 'Cargo', 'E-mail', 'telefone',
            'celular', 'contatos adicionais/notas', 'Setor/Área', 'Planilha', 'Aba'
        ]
        colunas_existentes = [col for col in colunas_para_exibir if col in resultados.columns]
        st.success(f"✅ {len(resultados)} resultado(s) encontrado(s).")
        st.dataframe(resultados[colunas_existentes])
    else:
        st.warning("Nenhum resultado encontrado para o CNPJ informado.")
