if cnpj_input:
    cnpj_limpo = limpar_cnpj(cnpj_input)

    # Busca parcial com contains, ignora NA
    resultado = df_total[df_total["CNPJ_LIMPO"].str.contains(cnpj_limpo, na=False)]

    if resultado.empty:
        st.warning("Nenhum contato encontrado com esse CNPJ.")
        st.write("⚠ Verifique se digitou o CNPJ sem pontos ou traços.")
        st.write("🧪 CNPJs disponíveis para teste:")
        st.dataframe(df_total[[coluna_cnpj, 'Planilha', 'Aba']].drop_duplicates())
    else:
        st.success(f"🎯 {len(resultado)} contato(s) encontrado(s).")
        
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
                    # Força string, tira espaços em branco nas extremidades
                    dados_exibicao[col_fixa] = resultado[cols_lower[nome_possivel]].astype(str).str.strip()
                    encontrada = True
                    break
            if not encontrada:
                dados_exibicao[col_fixa] = ""  # cria coluna vazia se não achou

        dados_exibicao['Planilha'] = resultado['Planilha'].astype(str).str.strip()
        dados_exibicao['Aba'] = resultado['Aba'].astype(str).str.strip()

        colunas_finais = ['CNPJ', 'Razão Social', 'Nome', 'Cargo', 'E-mail',
                         'telefone', 'celular', 'contatos adicionais/ notas', 'Setor/Área', 'Planilha', 'Aba']

        dados_exibicao = dados_exibicao[colunas_finais]

        st.dataframe(dados_exibicao, use_container_width=True)
