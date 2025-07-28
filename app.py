import streamlit as st
import pandas as pd
import zipfile
import os
from io import BytesIO
import tempfile

st.set_page_config(layout="wide")
st.title("📂 Buscador de informações por CNPJ")

# Mapeia nomes flexíveis para colunas padrão
def padronizar_colunas(df):
    colunas_padrao = {
        "CNPJ": ["cnpj"],
        "Razão Social": ["razao social", "razão social", "nome da empresa", "empresa"],
        "Nome": ["nome", "nome completo", "contato"],
        "Cargo": ["cargo", "função", "posição"],
        "E-mail": ["email", "e-mail", "e mail"],
        "Telefone": ["telefone", "tel", "telefone fixo"],
        "Celular": ["celular", "cel", "whatsapp", "zap"],
        "Contatos adicionais / notas": ["notas", "observação", "observações", "comentários", "anotação", "informações adicionais"]
    }

    colunas_encontradas = {}

    for padrao, variacoes in colunas_padrao.items():
        for var in variacoes:
            for col in df.columns:
                if var in col.lower():
                    colunas_encontradas[padrao] = col
                    break
            if padrao in colunas_encontradas:
                break

    return colunas_encontradas

uploaded_file = st.file_uploader("📁 Faça upload de um arquivo ZIP com as planilhas", type="zip")

if uploaded_file:
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "uploaded.zip")
        with open(zip_path, "wb") as f:
            f.write(uploaded_file.read())

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(tmpdir)

        resultados = []

        for filename in os.listdir(tmpdir):
            if filename.endswith(".xlsx") or filename.endswith(".xls"):
                planilha_path = os.path.join(tmpdir, filename)
                try:
                    xls = pd.ExcelFile(planilha_path)
                    for aba in xls.sheet_names:
                        try:
                            df = pd.read_excel(xls, sheet_name=aba, dtype=str)
                            df.columns = df.columns.str.strip()
                            colunas = padronizar_colunas(df)

                            dados = {
                                "CNPJ": df[colunas.get("CNPJ")] if "CNPJ" in colunas else "",
                                "Razão Social": df[colunas.get("Razão Social")] if "Razão Social" in colunas else "",
                                "Nome": df[colunas.get("Nome")] if "Nome" in colunas else "",
                                "Cargo": df[colunas.get("Cargo")] if "Cargo" in colunas else "",
                                "E-mail": df[colunas.get("E-mail")] if "E-mail" in colunas else "",
                                "Telefone": df[colunas.get("Telefone")] if "Telefone" in colunas else "",
                                "Celular": df[colunas.get("Celular")] if "Celular" in colunas else "",
                                "Contatos adicionais / notas": df[colunas.get("Contatos adicionais / notas")] if "Contatos adicionais / notas" in colunas else "",
                            }

                            df_resultado = pd.DataFrame(dados)
                            df_resultado["Planilha"] = filename
                            df_resultado["Aba"] = aba

                            resultados.append(df_resultado)
                        except Exception as e:
                            st.warning(f"Erro ao processar aba '{aba}' da planilha '{filename}': {e}")
                except Exception as e:
                    st.warning(f"Erro ao abrir planilha '{filename}': {e}")

        if resultados:
            resultado_final = pd.concat(resultados, ignore_index=True)

            # Reorganiza colunas na ordem desejada
            ordem_colunas = [
                "CNPJ", "Razão Social", "Nome", "Cargo", "E-mail",
                "Telefone", "Celular", "Contatos adicionais / notas",
                "Planilha", "Aba"
            ]
            for col in ordem_colunas:
                if col not in resultado_final.columns:
                    resultado_final[col] = ""

            resultado_final = resultado_final[ordem_colunas]

            st.success("✅ Dados extraídos com sucesso!")
            st.dataframe(resultado_final, use_container_width=True)

            # Download
            csv = resultado_final.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 Baixar resultado em CSV", csv, file_name="resultado_cnpjs.csv", mime='text/csv')
        else:
            st.error("❌ Nenhum dado foi extraído das planilhas enviadas.")
