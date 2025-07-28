import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import tempfile

# Autenticação
SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'credentials.json'

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)

FOLDER_NAME = 'Base teste'

def get_folder_id_by_name(folder_name):
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder'"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    folders = results.get('files', [])
    if folders:
        return folders[0]['id']
    return None

def list_files_in_folder(folder_id):
    query = f"'{folder_id}' in parents"
    results = drive_service.files().list(q=query, fields="files(id, name, mimeType)").execute()
    return results.get('files', [])

def download_and_read_file(file_id, filename):
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    ext = filename.lower().split('.')[-1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{ext}') as tmp_file:
        tmp_file.write(fh.read())
        tmp_file.flush()
        if ext == 'csv':
            return pd.read_csv(tmp_file.name, encoding='utf-8', engine='python', sep=None)
        elif ext in ['xlsx', 'xls']:
            return pd.read_excel(tmp_file.name, sheet_name=None)
        else:
            return None

def padronizar_colunas(df):
    colunas_padrao = {
        'cnpj': 'CNPJ',
        'razão social': 'Razão Social',
        'nome': 'Nome',
        'cargo': 'Cargo',
        'e-mail': 'E-mail',
        'email': 'E-mail',
        'telefone': 'Telefone',
        'celular': 'Celular',
        'contatos adicionais': 'Contatos Adicionais/Notas',
        'notas': 'Contatos Adicionais/Notas',
        'setor': 'Setor/Área',
        'área': 'Setor/Área',
    }
    novas_colunas = {}
    for col in df.columns:
        col_limpa = col.strip().lower()
        for chave in colunas_padrao:
            if chave in col_limpa:
                novas_colunas[col] = colunas_padrao[chave]
                break
    df = df.rename(columns=novas_colunas)
    return df[[col for col in colunas_padrao.values() if col in df.columns]]

def main():
    st.title('Busca de contatos por CNPJ')

    cnpj_input = st.text_input('Digite o CNPJ (com ou sem pontuação):')
    if not cnpj_input:
        st.stop()

    cnpj_input = ''.join(filter(str.isdigit, cnpj_input))

    folder_id = get_folder_id_by_name(FOLDER_NAME)
    files = list_files_in_folder(folder_id)

    resultados = []

    for file in files:
        nome_arquivo = file['name']
        try:
            conteudo = download_and_read_file(file['id'], nome_arquivo)
            if conteudo is None:
                continue

            if isinstance(conteudo, dict):  # múltiplas abas
                for aba_nome, df in conteudo.items():
                    if not isinstance(df, pd.DataFrame):
                        continue
                    df = padronizar_colunas(df)
                    if 'CNPJ' not in df.columns:
                        continue
                    df['CNPJ'] = df['CNPJ'].astype(str).str.replace(r'\D', '', regex=True)
                    resultado = df[df['CNPJ'] == cnpj_input].copy()
                    if not resultado.empty:
                        resultado['Planilha'] = nome_arquivo
                        resultado['Aba'] = aba_nome
                        resultados.append(resultado)
            else:
                df = padronizar_colunas(conteudo)
                if 'CNPJ' not in df.columns:
                    continue
                df['CNPJ'] = df['CNPJ'].astype(str).str.replace(r'\D', '', regex=True)
                resultado = df[df['CNPJ'] == cnpj_input].copy()
                if not resultado.empty:
                    resultado['Planilha'] = nome_arquivo
                    resultado['Aba'] = '(única aba)'
                    resultados.append(resultado)
        except Exception as e:
            st.warning(f'Erro ao ler arquivo {nome_arquivo}: {e}')

    if resultados:
        resultado_final = pd.concat(resultados, ignore_index=True)
        colunas_ordenadas = ['CNPJ', 'Razão Social', 'Nome', 'Cargo', 'E-mail',
                             'Telefone', 'Celular', 'Contatos Adicionais/Notas',
                             'Setor/Área', 'Planilha', 'Aba']
        colunas_existentes = [col for col in colunas_ordenadas if col in resultado_final.columns]
        st.success(f'{len(resultado_final)} resultado(s) encontrado(s):')
        st.dataframe(resultado_final[colunas_existentes])
    else:
        st.info('Nenhum resultado encontrado para este CNPJ.')

if __name__ == '__main__':
    main()
