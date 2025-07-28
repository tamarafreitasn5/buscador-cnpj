import streamlit as st

st.title("Teste de st.secrets")

# Mostra todas as chaves que o Streamlit carregou do secrets
st.write("Chaves disponíveis em st.secrets:", list(st.secrets.keys()))

# Verifica se a chave 'google_service_account' está presente
if "google_service_account" in st.secrets:
    st.success("✅ A chave 'google_service_account' está disponível no st.secrets!")
else:
    st.error("❌ A chave 'google_service_account' NÃO foi encontrada no st.secrets.")
