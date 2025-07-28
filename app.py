import streamlit as st
import pandas as pd
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Autenticação com st.secrets
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets.readonly"]
)

# ID da pasta no Google Drive (você pode pegar esse ID da URL da pasta)
FOLDER_NAME = "Base teste"
DRIVE_SERVICE = build("drive", "v3", credentials=credentials)
SHEETS_SERVICE = build("sheets", "v4", credentials=credentials)

# Função para encontrar o ID da pasta pelo nome
def get_folder_id_by_name(name):
    results = DRIVE_SERVICE.files().list(q=f"mimeType='application/vnd.google-apps.folder' and name='{name}'",
                                         fields="files(id)").execute()
    folders = results.get("files", [])
    if folders:
        return folders[0]["id"]
    return None

# Função para listar arquivos na pasta
def list_files_in_folder(folder_id):
    query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet'"
    results = DRIVE_SERVICE.files().list(q=query, fields="files(id, name)").execute()
    return results.get("files", [])

# Padronização de nomes de colunas (tolerante a maiúsculas, minúsculas, acentos, variações etc.)
def padronizar_nome(col):
    col = col.strip().lower()
    col = col.replace("razão social", "razao social")
    if "cnpj" in col:
        return "CNPJ"
    elif "razao" in col and "social" in col:
        return "Razão Social"
    elif "nome" in col and "empresa" in col:
        return "Razão Social"
    elif col in ["nome", "contato", "responsavel"]:
        return "Nome"
    elif "cargo" in col:
        return "Cargo"
    elif "email" in col:
        return "E-mail"
    elif "telefone" in col and "cel" in col:
        return "Celular"
    elif "telefone" in col:
        return "Telefone"
    elif "celular" in col:
        return "Celular"
    elif "nota" in col or "adicional" in col:
        return "Contatos adicionais/Notas"
    elif "setor" in col or "área" in col or "area" in col:
        return "Setor/Área"
    else:
        return col  # mantém original se não for reconhecido

# Função para buscar dados nas planilhas
def buscar_dados_por_cnpj(cnpj_input):
    folder_id = get_folder_id_by_name(FOLDER_NAME)
    arquivos = list_files_in_folder(folder_id)
    resultados = []

    for arquivo in arquivos:
        spreadsheet_id = arquivo["id"]
        nome_arquivo = arquivo["name"]

        # Lista as abas da planilha
        sheets_metadata = SHEETS_SERVICE.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        abas = sheets_metadata["sheets"]

        for aba in abas:
            nome_aba = aba["properties"]["title"]
            try:
                dados = SHEETS_SERVICE.spreadsheets().values().get(
                    spreadsheetId=spreadsheet_id,
                    range=f"'{nome_aba}'"
                ).execute()

                valores = dados.get("values", [])
                if not valores:
                    continue

                df = pd.DataFrame(valores[1:], columns=valores[0])

                # Padroniza os nomes das colunas
                df.columns = [padronizar_nome(c) for c in df.columns]

                # Normaliza o CNPJ para buscar
                df["CNPJ"] = df["CNPJ"].astype(str).str.replace(r"\D", "", regex=True)
                cnpj_input_limpo = cnpj_input.strip().replace(".", "").replace("/", "").replace("-", "")

                df_filtrado = df[df["CNPJ"].str.contains(cnpj_input_limpo, na=False, case=False)]

                if not df_filtrado.empty:
                    df_filtrado["Planilha"] = nome_arquivo
                    df_filtrado["Aba"] = nome_aba
                    resultados.append(df_filtrado)

            except Exception as e:
                print(f"Erro na aba {nome_aba} da planilha {nome_arquivo}: {e}")

    if resultados:
        df_resultado = pd.concat(resultados, ignore_index=True)
        colunas_desejadas = ["CNPJ", "Razão Social", "Nome", "Cargo", "E-mail", "Telefone", "Celular",
                             "Contatos adicionais/Notas", "Setor/Área", "Planilha", "Aba"]

        for col in colunas_desejadas:
            if col not in df_resultado.columns:
                df_resultado[col] = ""

        return df_resultado[colunas_desejadas]
    else:
        return pd.DataFrame(columns=["CNPJ", "Razão Social", "Nome", "Cargo", "E-mail", "Telefone", "Celular",
                                     "Contatos adicionais/Notas", "Setor/Área", "Planilha", "Aba"])

# Interface Streamlit
st.title("🔍 Buscador de CNPJ - Planilhas Google Drive")

cnpj_input = st.text_input("Digite o CNPJ para buscar:")

if st.button("Buscar"):
    if not cnpj_input:
        st.warning("Por favor, digite um CNPJ.")
    else:
        resultado = buscar_dados_por_cnpj(cnpj_input)
        if resultado.empty:
            st.error("Nenhum dado encontrado para esse CNPJ.")
        else:
            st.success(f"Encontrados {len(resultado)} registros.")
            st.dataframe(resultado)
