import streamlit as st

st.set_page_config(
    page_title="Ferramenta de Análise dos Microdados do ENEM",
    layout="wide"
)

st.title("📊 Ferramenta de Análise dos Microdados do ENEM")

st.markdown("""
    <style>
        button[data-testid="stExpandSidebarButton"] { display: none !important; }
        .st-emotion-cache-70qvj9 { display: none !important; }
    </style>
""", unsafe_allow_html=True)

tab1, tab_utils = st.tabs(["🏠 Geral", "⚙️ Utils"])

with tab1:
    st.markdown("## 🗂️ Escolha um módulo para começar:")

    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)

    with col1:
        if st.button("🔎 Exploração dos Dados", use_container_width=True):
            st.switch_page("pages/1_Exploration.py")

    with col2:
        if st.button("📈 Dashboards", use_container_width=True):
            st.switch_page("pages/2_Dashboards.py")

    with col3:
        if st.button("🤖 Predição de Desempenho", use_container_width=True):
            st.switch_page("pages/3_Prediction.py")

    with col4:
        if st.button("📝 Análise de Questões", use_container_width=True):
            st.switch_page("pages/4_Questions.py")

with tab_utils:
    st.markdown("## ⚙️ Utilitários")
    if st.button("📥 Abrir Parser de Gabaritos", use_container_width=True):
       st.switch_page("pages/5_gabarito_parser.py")
