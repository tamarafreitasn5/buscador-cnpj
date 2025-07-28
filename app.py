import streamlit as st
import pandas as pd
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
from io import BytesIO
from googleapiclient.http import MediaIoBaseDownload

# ====== CONFIGURAÇÕES ======
SCOPES = ['https://www.googleapis.com/auth/drive']
FOLDER_NAME = 'base teste'

# ====== AUTENTICAÇÃO ======
creds = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=SCOPES
)

drive_service = build('drive', 'v3', credentials=creds)
sheets_service = build('sheets', 'v4', credentials=creds)

# ====== FUNÇÕES AUXILIARES ======
def normalize_cnpj(cnpj):
    """Remove pontuação e deixa apenas os 14 números do CNPJ"""
    if pd.isna(cnpj):
        return ''
    return re.sub(r'\D', '', str(cnpj)).zfill(14)

def get_folder_id_by_name(folder_name):
    response = drive_service.files().list(
        q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
        spaces='drive',
        fields='files(id, name)').execute()
    folders = response.get('files', [])
    return folders[0]['id'] if folders else None

def list_excel_files_in_folder(folder_id):
    query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet' and trashed=false"
    response = drive_service.files().list(q=query, fields="files(id, name)").execute()
    return response.get('files', [])

def read_sheet(file_id, sheet_name):
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=file_id,
            range=sheet_name
        ).execute()
        values = result.get('values', [])
        if not values:
            return None
        df = pd.DataFrame(values[1:], columns=values[0])
        return df
    except Exception:
        return None

def list_sheet_names(file_id):
    try:
        sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=file_id).execute()
        return [sheet['properties']['title'] for sheet in sheet_metadata['sheets']]
    except Exception:
        return []

# ====== LÓGICA PRINCIPAL ======
folder_id = get_folder_id_by_name(FOLDER_NAME)
files = list_excel_files_in_folder(folder_id)

dados_combinados = []

for file in files:
    file_id = file['id']
    file_name = file['name']
    sheet_names = list_sheet_names(file_id)
    
    for sheet_name in sheet_names:
        df = read_sheet(file_id, sheet_name)
        if df is None or df.empty:
            continue

        # Padroniza colunas
        df.columns = [c.strip().lower() for c in df.columns]

        # Verifica se tem CNPJ
        cnpj_col = next((col for col in df.columns if 'cnpj' in col), None)
        if not cnpj_col:
            continue
        
        df['CNPJ'] = df[cnpj_col].apply(normalize_cnpj)

        # Renomeia/Padroniza
        mapeamento = {
            'razao social': 'Razão Social',
            'nome': 'Nome',
            'cargo': 'Cargo',
            'e-mail': 'E-mail',
            'email': 'E-mail',
            'telefone': 'telefone',
            'celular': 'celular',
            'notas': 'contatos adicionais/notas',
            'setor': 'Setor/Área',
            'área': 'Setor/Área'
        }

        for k, v in mapeamento.items():
            col = next((col for col in df.columns if k in col), None)
            if col:
                df[v] = df[col]

        df['Planilha'] = file_name
        df['Aba'] = sheet_name
        dados_combinados.append(df)

# ====== UNIFICAÇÃO FINAL ======
if dados_combinados:
    df_final = pd.concat(dados_combinados, ignore_index=True)

    colunas_exibir = [
        'CNPJ', 'Razão Social', 'Nome', 'Cargo', 'E-mail',
        'telefone', 'celular', 'contatos adicionais/notas', 'Setor/Área',
        'Planilha', 'Aba'
    ]

    for col in colunas_exibir:
        if col not in df_final.columns:
            df_final[col] = ''

    st.dataframe(df_final[colunas_exibir])
else:
    st.warning("Nenhum dado foi encontrado nas planilhas da pasta.")
