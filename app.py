        # Dicionário com possíveis nomes para cada coluna (com maiúsculas, minúsculas e variantes)
        aliases_colunas = {
            "CNPJ": ["CNPJ", "cnpj", "CNPJ_LIMPO", "cnpj_limpo"],
            "Razão Social": [
                "Razão Social", "RAZÃO SOCIAL", "razao social", "razaosocial",
                "empresa", "nomeempresa"
            ],
            "Nome": [
                "Nome", "NOME", "nome", "nome contato", "contato", "nomecontato"
            ],
            "Cargo": [
                "Cargo", "CARGO", "cargo", "posição", "posicao", "função",
                "funcao", "cargo/função"
            ],
            "E-mail": [
                "E-mail", "EMAIL", "email", "e-mail", "e mail"
            ],
            "Telefone": [
                "Telefone", "TELEFONE", "telefone", "tel", "telefonefixo",
                "telefoneresidencial"
            ],
            "Celular": [
                "Celular", "CELULAR", "celular", "telefonecelular", "whatsapp", "cel"
            ],
            "Contatos adicionais/notas": [
                "Contatos adicionais/notas", "contatos adicionais/notas",
                "Contatos adicionais", "contatos adicionais", "notas", "Notas",
                "observacoes", "observações", "comentarios", "comentários",
                "contatosadicionais", "notas/observações"
            ],
            "Setor/Área": [
                "Setor/Área", "SETOR/ÁREA", "Setor", "Área", "area", "segmento",
                "segmentacao"
            ],
            "Planilha": ["Planilha"],
            "Aba": ["Aba"]
        }
