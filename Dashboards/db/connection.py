import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import streamlit as st

_engine: Engine | None = None

def get_engine() -> Engine:
    """Retorna o engine do SQLAlchemy. Cria apenas uma vez."""
    global _engine
    if _engine is None:
        try:
            database_url = f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}?client_encoding=utf8"
            _engine = create_engine(database_url)
            # Teste de conexão
            with _engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            st.success("Conexão com PostgreSQL estabelecida com sucesso!")
        except Exception as e:
            st.error(f"Falha ao criar 'engine' ou conectar ao SQLAlchemy: {e}")
            st.info("Verifique a string de conexão, usuário, senha, host, porta e se o serviço PostgreSQL está ativo.")
            st.stop()
    return _engine