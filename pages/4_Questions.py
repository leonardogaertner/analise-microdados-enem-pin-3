import streamlit as st

st.markdown("""
    <style>
        button[data-testid="stExpandSidebarButton"] { display: none !important; }
        div[data-testid="stToolbar"] {visibility: hidden !important;}

        div.stButton > button {
            background: none;
            border: none;
            font-size: 22px;
            color: #FFFFFF;
            cursor: pointer;
            transition: 0.2s;
        }

        div.stButton > button:hover {
            color: #FF4B4B;
        }
    </style>
""", unsafe_allow_html=True)

if st.button("⬅", key="back_button"):
    st.switch_page("app.py")

st.title("📝 Análise de Questões")
st.info("Aqui você poderá analisar o conteúdo das questões do ENEM, filtrando por área, ano e outras características.")
