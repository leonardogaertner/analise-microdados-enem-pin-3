# Exploration/db_utils.py
import os
from sqlalchemy import create_engine
import streamlit as st

# Config de conexão
DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME', 'microdados')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASS = os.environ.get('DB_PASS', '123')

TABLE_NAME = "dados_enem_consolidado"


@st.cache_resource
def get_engine():
    """Cria e cacheia o engine do SQLAlchemy."""
    try:
        return create_engine(
            f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        )
    except Exception as e:
        st.error(f"Erro ao conectar ao banco de dados: {e}")
        return None


# ==========================================================
#  BASE QUERY COM JOIN NA TABELA RELATORIO_MUNICIPIOS
#  (Substitui os nomes de município pelos do relatório,
#   mas mantém os MESMOS nomes de coluna: NO_MUNICIPIO_PROVA / ESC)
# ==========================================================

# Subquery que enriquece os microdados com o nome oficial do município
BASE_SUBQUERY = f'''
    SELECT
        t1.*,
        mun_prova."NOME_MUNICIPIO" AS "NOME_MUNICIPIO_PROVA",
        mun_esc."NOME_MUNICIPIO"   AS "NOME_MUNICIPIO_ESC"
    FROM "{TABLE_NAME}" AS t1
    LEFT JOIN "RELATORIO_MUNICIPIOS" AS mun_prova
        ON t1."CO_MUNICIPIO_PROVA" = mun_prova."CO_MUNICIPIO"
    LEFT JOIN "RELATORIO_MUNICIPIOS" AS mun_esc
        ON t1."CO_MUNICIPIO_ESC" = mun_esc."CO_MUNICIPIO"
'''

# FROM comum para todos os lugares que precisarem consultar os dados enriquecidos
BASE_FROM_VIEW = f'FROM (\n{BASE_SUBQUERY}\n) AS base_enem'

# Usados pela parte de filtros / paginação / gráficos
BASE_QUERY = f'SELECT * {BASE_FROM_VIEW}'
BASE_COUNT_QUERY = f'SELECT COUNT(*) {BASE_FROM_VIEW}'
