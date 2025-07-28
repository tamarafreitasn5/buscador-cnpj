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

                # REMOVA ou comente as próximas linhas para evitar mostrar dados na tela
                # st.write(f"Planilha: {arquivo['name']} - Aba: {aba.title} - Exemplo:")
                # st.dataframe(df.head(3))

                df_total = pd.concat([df_total, df], ignore_index=True)
        except Exception as e:
            st.warning(f"Erro ao ler arquivo {arquivo['name']}: {e}")
    return df_total
