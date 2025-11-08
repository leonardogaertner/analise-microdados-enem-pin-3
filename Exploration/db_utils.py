# Exploration/db_utils.py
import os
from sqlalchemy import create_engine
import streamlit as st

DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
DB_PORT = os.environ.get('DB_PORT', '5433')
DB_NAME = os.environ.get('DB_NAME', 'microdados')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASS = os.environ.get('DB_PASS', 'admin')
TABLE_NAME = "dados_enem_consolidado"

@st.cache_resource
def get_engine():
    try:
        return create_engine(f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        return None