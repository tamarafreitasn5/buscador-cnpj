import streamlit as st
import pandas as pd
import os
import re

# Mapeamento de nomes de colunas para padronização
aliases_colunas = {
    "cnpj": ["cnpj", "CNPJ"],
    "razao_social": ["razão social", "razao social", "empresa"],
    "nome": ["nome", "contato", "nome completo", "nome do contato"],
    "cargo": ["cargo", "posição", "função"],
    "email": ["e-mail", "email", "mail"],
    "telefone": ["telefone", "tel", "telefone fixo"],
    "celular": ["celular", "telefone celular", "whatsapp"],
    "notas": ["notas", "observações", "comentários", "anotações", "contatos adicionais"],
    "setor": ["setor", "segmento", "ramo", "área"]
}

def padronizar_colunas(df):
    colunas_novas = {}
    for nova_col, aliases in aliases_colunas.items():
        for alias in aliases:
            for col in df.columns:
                if alias.lower() in str(col).lower():
                    colunas_novas[col] = nova_col
                    break
    return df.rename(columns=colunas_novas)

def processar_arquivo(path):
    if path.endswith(".csv"):
        df = pd.read_csv(path, encoding="utf-8", sep=None, engine="python")
    else:
        df = pd.read_excel(path, sheet_name=None)
    return df

def buscar_cnpj_em_df(df, cnpj_input):
    padronizado = padronizar_colunas(df)
    if "cnpj" not in padronizado.columns:
        return pd.DataFrame()
    padronizado["cnpj"] = padronizado["cnpj"].astype(str).str.replace(r'\D', '', regex=True)
    cnpj_limpo = re.sub(r'\D', '', cnpj_input)
    return padronizado[padronizado["cnpj"].str.contains(cnpj_limpo, na=False)]

def main():
    st.title("🔎 Buscador por CNPJ")
    pasta = st.text_input("📁 Caminho da pasta com os arquivos (Excel ou CSV):")

    cnpj_input = st.text_input("🔍 Digite o CNPJ para buscar:")
    if st.button("Buscar") and pasta and cnpj_input:
        resultados = []
        for nome_arquivo in os.listdir(pasta):
            caminho_completo = os.path.join(pasta, nome_arquivo)
            if not (nome_arquivo.endswith(".xlsx") or nome_arquivo.endswith(".csv")):
                continue

            dados = processar_arquivo(caminho_completo)
            if isinstance(dados, dict):  # Excel com várias abas
                for aba, df in dados.items():
                    resultado = buscar_cnpj_em_df(df, cnpj_input)
                    if not resultado.empty:
                        resultado["Planilha"] = nome_arquivo
                        resultado["Aba"] = aba
                        resultados.append(resultado)
            else:  # CSV
                resultado = buscar_cnpj_em_df(dados, cnpj_input)
                if not resultado.empty:
                    resultado["Planilha"] = nome_arquivo
                    resultado["Aba"] = "Única (CSV)"
                    resultados.append(resultado)

        if resultados:
            final = pd.concat(resultados, ignore_index=True)
            colunas_finais = [
                "cnpj", "razao_social", "nome", "cargo", "email",
                "telefone", "celular", "notas", "setor", "Planilha", "Aba"
            ]
            colunas_existentes = [col for col in colunas_finais if col in final.columns]
            st.dataframe(final[colunas_existentes])
        else:
            st.warning("Nenhum resultado encontrado para o CNPJ informado.")

if __name__ == "__main__":
    main()
