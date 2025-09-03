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


st.title("📈 Predição de Desempenho")
st.info("Nesta seção, você poderá utilizar modelos de predição para estimar o desempenho com base nos dados disponíveis.")
