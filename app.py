import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import pandas as pd
import re
import unidecode

st.set_page_config(page_title="Consulta por CNPJ", layout="wide")
st.title("🔍 Consulta de Contatos por CNPJ (Google Drive)")

# Configurações
FOLDER_NAME = "Base teste"

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/spreadsheets.readonly"
]

# AUTENTICAÇÃO usando st.secrets
service_account_info = st.secrets["google_service_account"]
creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
gc = gspread.authorize(creds)
drive_service = build('drive', 'v3', credentials=creds)

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

def list_spreadsheets_in_folder(folder_id):
    query = f"'{folder_id}' in parents and mimeType = 'application/vnd.google-apps.spreadsheet'"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    return results.get("files", [])

def carregar_planilhas_google_drive(folder_id):
    arquivos = list_spreadsheets_in_folder(folder_id)
    df_total = pd.DataFrame()
    for arquivo in arquivos:
        try:
            sh = gc.open_by_key(arquivo['id'])
            for aba in sh.worksheets():
                valores = aba.get_all_values()
                if not valores or len(valores) < 2:
                    continue
                header = valores[1]  # Cabeçalho linha 2
                dados = valores[2:]  # Dados a partir da linha 3

                df = pd.DataFrame(dados, columns=header)
                
                df.columns = [str(col).strip() for col in df.columns]
                
                for c in df.columns:
                    if df[c].dtype == 'object':
                        df[c] = df[c].astype(str).str.strip().replace({'': pd.NA, 'nan': pd.NA})

                df['Planilha'] = arquivo['name']
                df['Aba'] = aba.title

                df_total = pd.concat([df_total, df], ignore_index=True)
        except Exception as e:
            st.warning(f"Erro ao ler arquivo {arquivo['name']}: {e}")
    return df_total

def normalizar_coluna(nome):
    return unidecode.unidecode(nome.lower().strip().replace(" ", "").replace("_",""))

folder_id = get_folder_id_by_name(FOLDER_NAME)

if folder_id is None:
    st.error(f"Pasta '{FOLDER_NAME}' não encontrada no Google Drive.")
    st.stop()

st.write(f"Pasta '{FOLDER_NAME}' encontrada. Carregando planilhas...")

df_total = carregar_planilhas_google_drive(folder_id)

if df_total.empty:
    st.warning("Nenhuma planilha válida encontrada na pasta.")
    st.stop()

# Seleciona coluna que contém CNPJ (mantido igual)
colunas_possiveis = [col for col in df_total.columns if 'cnpj' in col.lower()]
if not colunas_possiveis:
    st.error("Nenhuma coluna com CNPJ encontrada nas planilhas.")
    st.stop()

coluna_cnpj = st.selectbox("Selecione a coluna que contém o CNPJ:", colunas_possiveis)

df_total["CNPJ_LIMPO"] = df_total[coluna_cnpj].apply(limpar_cnpj)

cnpj_input = st.text_input("Digite o CNPJ (pode ser parte, sem pontos ou traços):")

if cnpj_input:
    cnpj_limpo = limpar_cnpj(cnpj_input)
    resultado = df_total[df_total["CNPJ_LIMPO"].str.contains(cnpj_limpo, na=False)]

    if resultado.empty:
        st.warning("Nenhum contato encontrado com esse CNPJ.")
        st.write("⚠ Verifique se digitou o CNPJ sem pontos ou traços.")
        st.write("🧪 CNPJs disponíveis para teste:")
        st.dataframe(df_total[[coluna_cnpj, 'Planilha', 'Aba']].drop_duplicates())
    else:
        st.success(f"🎯 {len(resultado)} contato(s) encontrado(s).")

        aliases_colunas = {
            "CNPJ": ["cnpj", "CNPJ", "cnpj_limpo", "CNPJ_LIMPO"],
            "Razão Social": ["razao social", "razão social", "nome da empresa", "empresa", "nomeempresa", "razaosocial", "RAZÃO SOCIAL"],
            "Nome": ["nome", "nome contato", "contato", "nomecontato", "NOME"],
            "Cargo": ["cargo", "posição", "posicao", "função", "funcao", "cargo/função", "CARGO"],
            "E-mail": ["e-mail", "email", "e mail", "E-MAIL", "EMAIL"],
            "Telefone": ["telefone", "tel", "telefonefixo", "telefoneresidencial", "TELEFONE"],
            "Celular": ["celular", "telefonecelular", "whatsapp", "cel", "CELULAR"],
            "Contatos adicionais/notas": ["contatos adicionais", "notas", "observacoes", "observações", "comentarios", "comentários", "contatosadicionais", "notas/observações"],
            "Setor/Área": ["setor", "área", "area", "segmento", "segmentacao", "setor/area", "SETOR/ÁREA"],
            "Planilha": ["planilha"],
            "Aba": ["aba"]
        }

        cols_norm = {normalizar_coluna(c): c for c in resultado.columns}

        dados_exibicao = pd.DataFrame()

        for nome_col, lista_alias in aliases_colunas.items():
            achou = False
            for alias in lista_alias:
                alias_norm = normalizar_coluna(alias)
                if alias_norm in cols_norm:
                    dados_exibicao[nome_col] = resultado[cols_norm[alias_norm]]
                    achou = True
                    break
            if not achou:
                dados_exibicao[nome_col] = ""  # cria coluna vazia se não achar

        dados_exibicao = dados_exibicao.fillna("")
        st.dataframe(dados_exibicao, use_container_width=True)

else:
    st.info("Digite o CNPJ para buscar os contatos.")
