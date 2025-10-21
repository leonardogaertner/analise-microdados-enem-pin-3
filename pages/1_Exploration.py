import streamlit as st
import os
import pandas as pd
from sqlalchemy import create_engine

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

if st.button("Voltar", key="back_button"):
    st.switch_page("app.py")

st.title("Exploração dos Dados")
st.info("Aqui você pode explorar os microdados do ENEM com tabelas, filtros, cruzamentos etc.")

# Configurações do banco
DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
DB_PORT = os.environ.get('DB_PORT', '5433') #Meu PgAdmin tá na porta 5433, então mudem isso aqui quando forem usar pq o padrao é 5432
DB_NAME = os.environ.get('DB_NAME', 'microdados')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASS = os.environ.get('DB_PASS', 'admin')

# Conexão com o banco
@st.cache_resource
def get_engine():
    return create_engine(f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# Carregar os dados da tabela
@st.cache_data(ttl=3600)
def load_table_data(table_name, limit=100):
    engine = get_engine()
    query = f"SELECT * FROM {table_name}"
    if limit:
        query += f" LIMIT {limit}"
    query += ";"
    df = pd.read_sql(query, engine)
    return df

st.subheader("Tabela Completa: Microdados do ENEM")

TABLE_NAME = "dados_enem_consolidado"

PAGE_SIZE = 100
if 'page' not in st.session_state:
    st.session_state.page = 1

def change_page(delta):
    st.session_state.page = max(1, st.session_state.page + delta)

@st.cache_data(ttl=3600)
def load_paginated_data(table_name, page, page_size):
    engine = get_engine()
    offset = (page - 1) * page_size
    query = f"SELECT * FROM {table_name} LIMIT {page_size} OFFSET {offset};"
    df = pd.read_sql(query, engine)
    return df

TABLE_NAME = "dados_enem_consolidado"

try:
    # Carregar total de linhas no bd
    with st.spinner("Carregando total de registros..."):
        count_query = f"SELECT COUNT(*) FROM {TABLE_NAME};"
        total_rows = pd.read_sql(count_query, get_engine()).iloc[0, 0]
        st.session_state.total_rows = total_rows

    # Carregar dados da página atual
    df = load_paginated_data(TABLE_NAME, st.session_state.page, PAGE_SIZE)

    if df.empty:
        st.warning("Nenhum dado encontrado nesta página.")
    else:
        total_cols = len(df.columns)
        start_row = (st.session_state.page - 1) * PAGE_SIZE + 1
        end_row = start_row + len(df) - 1
        st.success(f"Página {st.session_state.page} | Linhas {start_row:,}–{end_row:,} | {total_cols} colunas")

        # Exibir a tabela
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Paginação do role
        col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])

        with col1:
            if st.button("⬅ Anterior", disabled=(st.session_state.page <= 1)):
                change_page(-1)
                st.rerun()

        with col2:
            st.write(f"**Página {st.session_state.page}**")

        with col3:
            total_pages = (st.session_state.total_rows + PAGE_SIZE - 1) // PAGE_SIZE
            st.caption(f"Total: {st.session_state.total_rows:,} linhas → {total_pages} páginas")
            # Input para escolher página específica
            page_input = st.number_input(
                "Ir para página",
                min_value=1,
                max_value=total_pages,
                value=st.session_state.page,
                step=1,
                key="page_input"
            )
            if st.session_state.page_input != st.session_state.page:
                st.session_state.page = page_input
                st.rerun()

        with col4:
            has_more = len(df) == PAGE_SIZE
            if st.button("Próximo ➡", disabled=not has_more):
                change_page(1)
                st.rerun()

        # Download (Tem que ver se faz sentido realmente o download em PDF)
        csv = df.to_csv(index=False, encoding='utf-8')
        st.download_button(
            label="📥 Baixar esta página como CSV",
            data=csv,
            file_name=f"{TABLE_NAME}_pagina_{st.session_state.page}.csv",
            mime="text/csv"
        )
        # Pra baixar tudo teria que usar limit=None

except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.code(f"""
    Verifique:
    - Tabela '{TABLE_NAME}' existe?
    - Banco está rodando em {DB_HOST}:{DB_PORT}?
    - Credenciais corretas?
    """)