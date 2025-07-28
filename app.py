import streamlit as st
import pandas as pd
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
import tempfile
import re

st.set_page_config(page_title="Consulta por CNPJ", layout="wide")
st.title("🔍 Consulta de Contatos por CNPJ (Google Drive)")

# Configurações
FOLDER_NAME = "Base teste"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly", "https://www.googleapis.com/auth/spreadsheets.readonly"]

# Autenticação via st.secrets
service_account_info = st.secrets["google_service_account"]
credentials = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=credentials)

def limpar_cnpj(cnpj):
    if pd.isna(cnpj):
        return ''
    return re.sub(r'\D', '', str(cnpj))

def get_folder_id_by_name(folder_name):
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder'"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    folders = results.get("files", [])
    if folders:
        return folders[0]["id"]
    else:
        return None

def list_files_in_folder(folder_id):
    query = f"'{folder_id}' in parents and (mimeType='application/vnd.google-apps.spreadsheet' or mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' or mimeType='text/csv')"
    results = drive_service.files().list(q=query, fields="files(id, name, mimeType)").execute()
    return results.get("files", [])

def download_and_read_file(file_id, filename, mime_type):
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
        if mime_type == 'application/vnd.google-apps.spreadsheet':
            # Para planilhas Google Sheets, vamos abrir via API gspread (já autenticado)
            import gspread
            gc = gspread.authorize(credentials)
            sh = gc.open_by_key(file_id)
            dfs = []
            for aba in sh.worksheets():
                valores = aba.get_all_values()
                if not valores or len(valores) < 2:
                    continue
                header = valores[1]
                dados = valores[2:]
                df = pd.DataFrame(dados, columns=header)
                df.columns = [str(col).strip() for col in df.columns]
                dfs.append((df, aba.title))
            return dfs  # retorna lista de (dataframe, nome_aba)
        elif ext in ['xlsx', 'xls']:
            xls = pd.ExcelFile(tmp_file.name)
            dfs = []
            for sheet_name in xls.sheet_names:
                df = xls.parse(sheet_name)
                dfs.append((df, sheet_name))
            return dfs
        elif ext == 'csv':
            df = pd.read_csv(tmp_file.name, encoding='utf-8', engine='python', sep=None)
            return [(df, '(única aba)')]
        else:
            return []

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
        col_limpa = str(col).strip().lower()
        for chave in colunas_padrao:
            if chave in col_limpa:
                novas_colunas[col] = colunas_padrao[chave]
                break
    df = df.rename(columns=novas_colunas)
    return df

def carregar_planilhas(folder_id):
    arquivos = list_files_in_folder(folder_id)
    df_total = pd.DataFrame()
    for arquivo in arquivos:
        try:
            dfs = download_and_read_file(arquivo['id'], arquivo['name'], arquivo['mimeType'])
            for df, aba_nome in dfs:
                df = padronizar_colunas(df)
                if 'CNPJ' not in df.columns:
                    continue
                for c in df.columns:
                    if df[c].dtype == 'object':
                        df[c] = df[c].astype(str).str.strip().replace({'': pd.NA, 'nan': pd.NA})
                df['CNPJ'] = df['CNPJ'].astype(str).str.replace(r'\D', '', regex=True)
                df['Planilha'] = arquivo['name']
                df['Aba'] = aba_nome
                df_total = pd.concat([df_total, df], ignore_index=True)
        except Exception as e:
            st.warning(f"Erro ao ler arquivo {arquivo['name']}: {e}")
    return df_total

folder_id = get_folder_id_by_name(FOLDER_NAME)

if folder_id is None:
    st.error(f"Pasta '{FOLDER_NAME}' não encontrada no Google Drive.")
    st.stop()

st.write(f"Pasta '{FOLDER_NAME}' encontrada. Carregando planilhas...")

df_total = carregar_planilhas(folder_id)

if df_total.empty:
    st.warning("Nenhuma planilha válida encontrada na pasta.")
    st.stop()

colunas_possiveis = [col for col in df_total.columns if 'cnpj' in col.lower()]
if not colunas_possiveis:
    st.error("Nenhuma coluna com CNPJ encontrada nas planilhas.")
    st.stop()

coluna_cnpj = st.selectbox("Selecione a coluna que contém o CNPJ:", colunas_possiveis)

cnpj_input = st.text_input("Digite o CNPJ (pode ser parte, sem pontos ou traços):")

if cnpj_input:
    cnpj_limpo = limpar_cnpj(cnpj_input)
    resultado = df_total[df_total["CNPJ"].str.contains(cnpj_limpo, na=False)]

    if resultado.empty:
        st.warning("Nenhum contato encontrado com esse CNPJ.")
        st.write("⚠ Verifique se digitou o CNPJ sem pontos ou traços.")
        st.write("🧪 CNPJs disponíveis para teste:")
        st.dataframe(df_total[[coluna_cnpj, 'Planilha', 'Aba']].drop_duplicates())
    else:
        st.success(f"🎯 {len(resultado)} contato(s) encontrado(s).")

        aliases_colunas = {
            "CNPJ": ["CNPJ", "cnpj", "CNPJ_LIMPO", "cnpj_limpo"],
            "Razão Social": ["Razão Social", "RAZÃO SOCIAL", "razao social", "razaosocial", "empresa", "nomeempresa"],
            "Nome": ["Nome", "NOME", "nome", "nome contato", "contato", "nomecontato"],
            "Cargo": ["Cargo", "CARGO", "cargo", "posição", "posicao", "função", "funcao", "cargo/função"],
            "E-mail": ["E-mail", "EMAIL", "email", "e-mail", "e mail"],
            "Telefone": ["Telefone", "TELEFONE", "telefone", "tel", "telefonefixo", "telefoneresidencial"],
            "Celular": ["Celular", "CELULAR", "celular", "telefonecelular", "whatsapp", "cel"],
            "Contatos adicionais/notas": ["Contatos adicionais/notas", "Contatos adicionais", "notas", "Notas", "observacoes", "observações", "comentarios", "comentários", "contatosadicionais", "notas/observações"],
            "Setor/Área": ["Setor/Área", "SETOR/ÁREA", "Setor", "Área", "area", "segmento", "segmentacao"],
            "Planilha": ["Planilha"],
            "Aba": ["Aba"]
        }

        dados_exibicao = pd.DataFrame()

        for nome_col, possiveis_nomes in aliases_colunas.items():
            coluna_encontrada = None
            for nome in possiveis_nomes:
                if nome in resultado.columns:
                    coluna_encontrada = nome
                    break
            if coluna_encontrada:
                dados_exibicao[nome_col] = resultado[coluna_encontrada].fillna("")
            else:
                dados_exibicao[nome_col] = ""

        st.dataframe(dados_exibicao, use_container_width=True)
else:
    st.info("Digite o CNPJ para buscar os contatos.")
