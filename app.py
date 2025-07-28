import streamlit as st
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
import io
from googleapiclient.http import MediaIoBaseDownload

# Autenticação
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=["https://www.googleapis.com/auth/drive"]
)
drive_service = build("drive", "v3", credentials=credentials)
sheets_service = build("sheets", "v4", credentials=credentials)

# Nome da pasta no Drive
FOLDER_ID = "19LsEdkxcp-PfdpL5ZE-PA257u51umlld"

# Mapeamento de possíveis nomes de colunas
COLUMN_MAP = {
    "cnpj": "CNPJ",
    "razão social": "Razão Social",
    "razao social": "Razão Social",
    "nome da empresa": "Razão Social",
    "nome": "Nome",
    "cargo": "Cargo",
    "e-mail": "E-mail",
    "email": "E-mail",
    "telefone": "Telefone",
    "celular": "Celular",
    "contatos adicionais": "Contatos adicionais/Notas",
    "notas": "Contatos adicionais/Notas",
    "setor": "Setor/Área",
    "área": "Setor/Área",
    "area": "Setor/Área",
}

def padronizar_colunas(df):
    new_columns = {}
    for col in df.columns:
        nome_original = col.strip().lower()
        if nome_original in COLUMN_MAP:
            new_columns[col] = COLUMN_MAP[nome_original]
    return df.rename(columns=new_columns)

def get_google_sheets_files(folder_id):
    query = f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.spreadsheet'"
    response = drive_service.files().list(q=query, fields="files(id, name)").execute()
    return response.get("files", [])

def get_sheet_data(file_id, sheet_name):
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=file_id,
            range=sheet_name
        ).execute()
        values = result.get("values", [])
        if not values:
            return pd.DataFrame()
        df = pd.DataFrame(values[1:], columns=values[0])
        df = padronizar_colunas(df)
        return df
    except Exception:
        return pd.DataFrame()

def get_sheet_names(file_id):
    try:
        sheet_metadata = sheets_service.spreadsheets().get(spreadsheetId=file_id).execute()
        return [s["properties"]["title"] for s in sheet_metadata["sheets"]]
    except Exception:
        return []

def buscar_dados_por_cnpj(cnpj_input):
    arquivos = get_google_sheets_files(FOLDER_ID)
    resultados = []

    for arquivo in arquivos:
        sheet_id = arquivo["id"]
        sheet_nome = arquivo["name"]
        abas = get_sheet_names(sheet_id)

        for aba in abas:
            df = get_sheet_data(sheet_id, aba)
            if "CNPJ" not in df.columns:
                continue

            df["CNPJ"] = df["CNPJ"].astype(str).str.replace(r'\D', '', regex=True)
            cnpj_formatado = cnpj_input.replace(".", "").replace("/", "").replace("-", "")
            df_filtrado = df[df["CNPJ"].str.contains(cnpj_formatado, na=False)]

            if not df_filtrado.empty:
                df_filtrado["Planilha"] = sheet_nome
                df_filtrado["Aba"] = aba
                resultados.append(df_filtrado)

    if resultados:
        resultado_final = pd.concat(resultados, ignore_index=True)
        colunas_finais = ['CNPJ', 'Razão Social', 'Nome', 'Cargo', 'E-mail', 'Telefone', 'Celular',
                          'Contatos adicionais/Notas', 'Setor/Área', 'Planilha', 'Aba']
        for col in colunas_finais:
            if col not in resultado_final.columns:
                resultado_final[col] = ""
        return resultado_final[colunas_finais]
    else:
        return pd.DataFrame(columns=[
            'CNPJ', 'Razão Social', 'Nome', 'Cargo', 'E-mail', 'Telefone', 'Celular',
            'Contatos adicionais/Notas', 'Setor/Área', 'Planilha', 'Aba'
        ])

# --- INTERFACE STREAMLIT ---
st.title("🔎 Buscador de CNPJ - Planilhas no Google Drive")

cnpj_input = st.text_input("Digite o CNPJ (com ou sem pontuação):")

if cnpj_input:
    resultado = buscar_dados_por_cnpj(cnpj_input)

    if not resultado.empty:
        st.success(f"{len(resultado)} resultado(s) encontrado(s).")
        st.dataframe(resultado)
        csv = resultado.to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ Baixar resultados em CSV", data=csv, file_name="resultado_cnpj.csv", mime="text/csv")
    else:
        st.warning("Nenhum dado encontrado para esse CNPJ.")
