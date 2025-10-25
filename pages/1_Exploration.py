import streamlit as st
import os
import pandas as pd
from sqlalchemy import create_engine
import numpy as np

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

# ======= Navegação =======
if st.button("Voltar", key="back_button"):
    st.switch_page("app.py")

st.title("Exploração dos Dados")
st.info("Aqui você pode explorar os microdados do ENEM com tabelas, filtros, cruzamentos etc.")

# Configurações do banco
DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
DB_PORT = os.environ.get('DB_PORT', '5432')
DB_NAME = os.environ.get('DB_NAME', 'microdados')
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASS = os.environ.get('DB_PASS', 'admin')

# Conexão com o banco
@st.cache_resource
def get_engine():
    return create_engine(f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

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
    return pd.read_sql(query, engine)

# Função dos filtros
def filter_dataframe(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    st.markdown("### 🔎 Filtros")

    col_toggle, col_clear = st.columns([1, 3])

    # Estado do filtro
    if "filters_active" not in st.session_state:
        st.session_state.filters_active = False

    # Checkbox ativar filtros
    modify = col_toggle.checkbox(
        f"Ativar filtros",
        value=st.session_state.filters_active,
        key=f"filter_checkbox_{table_name}_{st.session_state.page}"
    )

    # Botão limpar filtros
    if col_clear.button("🔁 Limpar filtros", key=f"clear_filters_{table_name}_{st.session_state.page}"):
        # Limpa todos os filtros selecionados
        for key in list(st.session_state.keys()):
            if key.startswith(f"{table_name}_") or key.startswith(f"filter_"):
                del st.session_state[key]
        
        # Desmarca a flag de filtros ativos
        st.session_state.filters_active = False
        st.session_state[f"filter_checkbox_{table_name}_{st.session_state.page}"] = False
        st.rerun()

    st.session_state.filters_active = modify

    if not modify:
        return df

    df = df.copy()

    to_filter_columns = st.multiselect(
        "Selecione colunas para filtrar:",
        df.columns,
        key=f"filter_columns_{table_name}_{st.session_state.page}"
    )

    for column in to_filter_columns:
        col1, col2 = st.columns((0.01, 4))
        key_prefix = f"{table_name}_{column}_{st.session_state.page}"

        # Ignora colunas vazias, se não da erro no streamlit
        if df[column].dropna().empty:
            col2.info(f"⚠️ Coluna '{column}' sem valores disponíveis para filtragem.")
            continue

        # Numéricos
        if pd.api.types.is_numeric_dtype(df[column]):
            _min = float(df[column].min())
            _max = float(df[column].max())

            if _min == _max:
                col2.info(f"ℹ️ Coluna '{column}' contém apenas um valor ({_min}).")
                continue

            user_min, user_max = col2.slider(
                f"Faixa de {column}",
                min_value=_min,
                max_value=_max,
                value=(_min, _max),
                key=f"slider_{key_prefix}"
            )
            df = df[df[column].between(user_min, user_max)]

        # Datas
        elif pd.api.types.is_datetime64_any_dtype(df[column]):
            if df[column].notnull().sum() == 0:
                col2.info(f"⚠️ Coluna '{column}' não possui datas válidas.")
                continue

            user_date = col2.date_input(
                f"Intervalo de {column}",
                value=(df[column].min(), df[column].max()),
                key=f"date_{key_prefix}"
            )
            if isinstance(user_date, tuple) and len(user_date) == 2:
                start_date, end_date = user_date
                df = df[df[column].between(pd.to_datetime(start_date), pd.to_datetime(end_date))]

        # Texto / Categórico
        elif pd.api.types.is_object_dtype(df[column]) or pd.api.types.is_categorical_dtype(df[column]):
            unique_values = df[column].dropna().unique()
            if len(unique_values) == 0:
                col2.info(f"⚠️ Coluna '{column}' sem valores válidos para seleção.")
                continue
            selected_values = col2.multiselect(
                f"Valores de {column}",
                unique_values,
                key=f"multi_{key_prefix}"
            )
            if selected_values:
                df = df[df[column].isin(selected_values)]

        # Caso tenha algum tipo de dado não tratado, cai nessa validação aqui
        else:
            col2.warning(f"Tipo de dado da coluna '{column}' não é suportado para filtragem.")
   
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
        # Aplicar filtros
        df_filtered = filter_dataframe(df, TABLE_NAME)

        total_cols = len(df_filtered.columns)
        start_row = (st.session_state.page - 1) * PAGE_SIZE + 1
        end_row = start_row + len(df_filtered) - 1
        st.success(f"Página {st.session_state.page} | Linhas {start_row:,}–{end_row:,} | {total_cols} colunas")

        # Exibir tabela filtrada
        st.dataframe(df_filtered, use_container_width=True, hide_index=True)

        # Download (Tem que ver se faz sentido realmente o download em PDF)
        csv = df_filtered.to_csv(index=False, encoding='utf-8')
        st.download_button(
            label="📥 Baixar esta página filtrada como CSV",
            data=csv,
            file_name=f"{TABLE_NAME}_pagina_{st.session_state.page}_filtrada.csv",
            mime="text/csv"
        )
        # Pra baixar tudo teria que usar limit=None


        # 🔄 Paginação
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

except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.code(f"""
    Verifique:
    - Tabela '{TABLE_NAME}' existe?
    - Banco está rodando em {DB_HOST}:{DB_PORT}?
    - Credenciais corretas?
    """)