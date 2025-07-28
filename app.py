import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import pandas as pd
import re

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
                # Cabeçalho na linha 2 (index 1)
                header = valores[1]
                dados = valores[2:]  # dados a partir da linha 3
                df = pd.DataFrame(dados, columns=header)
                df.columns = [str(col).strip() for col in df.columns]
                df['Planilha'] = arquivo['name']
                df['Aba'] = aba.title
                df_total = pd.concat([df_total, df], ignore_index=True)
        except Exception as e:
            st.warning(f"Erro ao ler arquivo {arquivo['name']}: {e}")
    return df_total

folder_id = get_folder_id_by_name(FOLDER_NAME)

if folder_id is None:
    st.error(f"Pasta '{FOLDER_NAME}' não encontrada no Google Drive.")
    st.stop()

st.write(f"Pasta '{FOLDER_NAME}' encontrada. Carregando planilhas...")

df_total = carregar_planilhas_google_drive(folder_id)

if df_total.empty:
    st.warning("Nenhuma planilha válida encontrada na pasta.")
    st.stop()

# Seleciona coluna que contém CNPJ
colunas_possiveis = [col for col in df_total.columns if 'cnpj' in col.lower()]
if not colunas_possiveis:
    st.error("Nenhuma coluna com CNPJ encontrada nas planilhas.")
    st.stop()

coluna_cnpj = st.selectbox("Selecione a coluna que contém o CNPJ:", colunas_possiveis)

# Limpa CNPJ para busca
df_total["CNPJ_LIMPO"] = df_total[coluna_cnpj].apply(limpar_cnpj)

# Input do usuário
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

        # Mapeamento de aliases para as colunas que você quer mostrar
        aliases_colunas = {
            'CNPJ': ['cnpj'],
            'Razão Social': ['razão social', 'razao social', 'nome da empresa', 'empresa', 'nome empresa'],
            'Nome': ['nome', 'nome contato', 'contato'],
            'Cargo': ['cargo', 'posição', 'posicao', 'função', 'funcao', 'cargo/função'],
            'E-mail': ['e-mail', 'email', 'e mail'],
            'telefone': ['telefone', 'tel', 'telefone fixo'],
            'celular': ['celular', 'telefone celular', 'whatsapp'],
            'contatos adicionais/ notas': ['contatos adicionais', 'notas', 'observações', 'observacoes', 'comentários', 'comentarios'],
            'Setor/Área': ['setor', 'área', 'area', 'segmento', 'segmentação']
        }

        cols_lower = {col.lower(): col for col in resultado.columns}
        dados_exibicao = pd.DataFrame()

        for col_fixa, possiveis_nomes in aliases_colunas.items():
            encontrada = False
            for nome_possivel in possiveis_nomes:
                if nome_possivel in cols_lower:
                    dados_exibicao[col_fixa] = resultado[cols_lower[nome_possivel]]
                    encontrada = True
                    break
            if not encontrada:
                dados_exibicao[col_fixa] = ""

        # Sempre mostra Planilha e Aba
        dados_exibicao['Planilha'] = resultado['Planilha']
        dados_exibicao['Aba'] = resultado['Aba']

        colunas_finais = ['CNPJ', 'Razão Social', 'Nome', 'Cargo', 'E-mail',
                         'telefone', 'celular', 'contatos adicionais/ notas', 'Setor/Área', 'Planilha', 'Aba']

        dados_exibicao = dados_exibicao[colunas_finais]

        st.dataframe(dados_exibicao, use_container_width=True)

else:
    st.info("Digite o CNPJ para buscar os contatos.")
