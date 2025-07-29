import streamlit as st
import pandas as pd
import os

# Função para padronizar os nomes das colunas
def padronizar_colunas(df):
    aliases_colunas = {
        'cnpj': 'CNPJ',
        'razão social': 'Razão Social',
        'nome': 'Nome',
        'cargo': 'Cargo',
        'email': 'E-mail',
        'telefone': 'Telefone',
        'celular': 'Celular',
        'contato adicional': 'Contatos adicionais/Notas',
        'setor': 'Setor/Área',
        'área': 'Setor/Área',
        'notas': 'Contatos adicionais/Notas'
    }

    colunas_novas = {}
    for col in df.columns:
        nome_original = col
        col = col.strip().lower()
        for chave, padrao in aliases_colunas.items():
            if chave in col:
                colunas_novas[nome_original] = padrao
                break
    df = df.rename(columns=colunas_novas)
    return df

# Interface
st.markdown("### 🔎 Buscador por CNPJ")
folder_path = st.text_input("📁 Caminho da pasta com os arquivos (Excel ou CSV):")
cnpj_input = st.text_input("🔍 Digite o CNPJ para buscar:")

if folder_path and cnpj_input:
    resultados = []
    for file_name in os.listdir(folder_path):
        if file_name.endswith((".xlsx", ".csv")) and not file_name.startswith("~$"):
            file_path = os.path.join(folder_path, file_name)
            try:
                if file_name.endswith(".csv"):
                    df_all = pd.read_csv(file_path, encoding='utf-8', sep=None, engine='python')
                    df_all = padronizar_colunas(df_all)
                    df_all["Planilha"] = file_name
                    df_all["Aba"] = "-"
                    df_filtrado = df_all[df_all.apply(lambda row: row.astype(str).str.contains(cnpj_input).any(), axis=1)]
                    if not df_filtrado.empty:
                        resultados.append(df_filtrado)
                else:
                    xls = pd.ExcelFile(file_path)
                    for aba in xls.sheet_names:
                        df = xls.parse(aba)
                        df = padronizar_colunas(df)
                        df["Planilha"] = file_name
                        df["Aba"] = aba
                        df_filtrado = df[df.apply(lambda row: row.astype(str).str.contains(cnpj_input).any(), axis=1)]
                        if not df_filtrado.empty:
                            resultados.append(df_filtrado)
            except Exception as e:
                st.warning(f"Erro ao ler {file_name}: {e}")

    if resultados:
        df_resultado = pd.concat(resultados, ignore_index=True)
        colunas_desejadas = ['CNPJ', 'Razão Social', 'Nome', 'Cargo', 'E-mail', 'Telefone', 'Celular',
                             'Contatos adicionais/Notas', 'Setor/Área', 'Planilha', 'Aba']
        colunas_presentes = [col for col in colunas_desejadas if col in df_resultado.columns]
        df_resultado = df_resultado[colunas_presentes]
        st.success(f"{len(df_resultado)} resultado(s) encontrado(s).")
        st.dataframe(df_resultado)
    else:
        st.error("Nenhum resultado encontrado.")
