import streamlit as st
import os
import pandas as pd
from sqlalchemy import create_engine
import numpy as np
from fpdf import FPDF
from Exploration import column_config

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
DB_PASS = os.environ.get('DB_PASS', 'aluno')

# Conexão com o banco
@st.cache_resource
def get_engine():
    return create_engine(f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

if 'page' not in st.session_state:
    st.session_state.page = 1
if 'page_size' not in st.session_state:
    st.session_state.page_size = 100

def change_page(delta):
    st.session_state.page = max(1, st.session_state.page + delta)

@st.cache_data(ttl=3600)
def load_paginated_data(table_name, page, page_size):
    engine = get_engine()

    # Base do SELECT
    base_query = f"""
        SELECT 
            t1.*,
            mun_prova."NOME_MUNICIPIO" AS "NOME_MUNICIPIO_PROVA",
            mun_esc."NOME_MUNICIPIO" AS "NOME_MUNICIPIO_ESC"
        FROM "{table_name}" AS t1
        LEFT JOIN "RELATORIO_MUNICIPIOS" AS mun_prova ON t1."CO_MUNICIPIO_PROVA" = mun_prova."CO_MUNICIPIO"
        LEFT JOIN "RELATORIO_MUNICIPIOS" AS mun_esc ON t1."CO_MUNICIPIO_ESC" = mun_esc."CO_MUNICIPIO"
    """

    # Paginação
    if page_size == "Todos":
        query = base_query + ";"
    else:
        offset = (page - 1) * page_size
        query = base_query + f" LIMIT {page_size} OFFSET {offset};"

    return pd.read_sql(query, engine)

# Função para criar o PDF (.csv segue fazendo infinitamente mais sentido)
def dataframe_to_pdf_bytes(df: pd.DataFrame) -> bytes:
    """
    Converte um DataFrame do Pandas em bytes de um PDF.
    A tabela será em modo paisagem (Landscape) para caber mais colunas.
    """
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()
    
    pdf.set_font("Arial", size=8) 
    
    df_str = df.fillna('N/A').astype(str)
    
    # Calcula larguras de coluna (distribuição igual)
    num_cols = len(df_str.columns)
    page_width = pdf.w - 2 * pdf.l_margin
    col_width = page_width / num_cols
    line_height = pdf.font_size * 2

    # Renderiza o Cabeçalho
    pdf.set_font(family=pdf.font_family, style="B", size=pdf.font_size)
    for col in df_str.columns:
        pdf.cell(col_width, line_height, col, border=1, align='C') 
    pdf.ln(line_height)
    pdf.set_font(family=pdf.font_family, style="", size=pdf.font_size)

    for _, row in df_str.iterrows():
        for col in df_str.columns:
            pdf.cell(col_width, line_height, row[col], border=1, align='L')
        pdf.ln(line_height)

    return pdf.output(dest='S').encode('latin-1')


# Função dos filtros
def filter_dataframe(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    st.markdown("### 🔎 Filtros")

    col_toggle, col_clear = st.columns([1, 3])

    if "filters_active" not in st.session_state:
        st.session_state.filters_active = False

    # Checkbox ativar filtros
    modify = col_toggle.checkbox(
        f"Ativar filtros",
        value=st.session_state.filters_active,
        key=f"filter_checkbox_{table_name}" 
    )

    # Botão limpar filtros
    if col_clear.button("🔁 Limpar filtros", key=f"clear_filters_{table_name}"):
        for key in list(st.session_state.keys()):
            if key.startswith(f"{table_name}_") or key.startswith(f"filter_"):
                del st.session_state[key]
        
        # Desmarca a flag de filtros ativos
        st.session_state.filters_active = False
        st.rerun()

    st.session_state.filters_active = modify

    if not modify:
        return df

    df = df.copy()

    to_filter_columns = st.multiselect(
        "Selecione colunas para filtrar:",
        df.columns,
        key=f"filter_columns_{table_name}"
    )

    for column in to_filter_columns:
        col1, col2 = st.columns((0.01, 4))
        key_prefix = f"{table_name}_{column}"

        if df[column].dropna().empty:
            col2.info(f"⚠️ Coluna '{column}' sem valores disponíveis para filtragem.")
            continue

        # Numéricos
        if pd.api.types.is_numeric_dtype(df[column]):
            # Se a coluna for um código, usa um tratamento especial (multiselect)
            if column.upper().startswith('CÓD.'):
                df = tratar_filtro_codigo(df, column, col2, key_prefix)
                continue # Pula para a próxima coluna no loop
            
            _min = int(np.floor(df[column].min()))
            _max = int(np.ceil(df[column].max()))

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

def tratar_filtro_codigo(df: pd.DataFrame, column: str, st_column_object, key_prefix: str) -> pd.DataFrame:
    """
    Cria um filtro multiselect para colunas numéricas que representam códigos.
    """
    # Pega os valores únicos da coluna, remove nulos e converte para inteiro
    unique_values = sorted([int(v) for v in df[column].dropna().unique()])
    
    if not unique_values:
        st_column_object.info(f"⚠️ Coluna de código '{column}' sem valores válidos para seleção.")
        return df

    # Cria o widget multiselect para o usuário escolher os códigos
    selected_values = st_column_object.multiselect(
        f"Selecione os valores de {column}",
        options=unique_values,
        key=f"multi_{key_prefix}"
    )

    # Se o usuário selecionou algum valor, filtra o DataFrame
    if selected_values:
        df = df[df[column].isin(selected_values)]
        
    return df

TABLE_NAME = "dados_enem_consolidado"
try:
    with st.spinner("Carregando total de registros..."):
        count_query = f"SELECT COUNT(*) FROM {TABLE_NAME};"
        total_rows = pd.read_sql(count_query, get_engine()).iloc[0, 0]
        st.session_state.total_rows = total_rows

    df = load_paginated_data(TABLE_NAME, st.session_state.page, st.session_state.page_size)
    df.columns = df.columns.str.upper()
    df = df.rename(columns=column_config.COLUMN_MAPPING)

    if df.empty:
        st.warning("Nenhum dado encontrado nesta página.")
    else:
        df_filtered = filter_dataframe(df, TABLE_NAME)

        st.dataframe(df_filtered, use_container_width=True, hide_index=True)
        
        # Paginação
        
        if st.session_state.page_size == "Todos":
            total_pages = 1
        else:
            total_pages = (st.session_state.total_rows + st.session_state.page_size - 1) // st.session_state.page_size
            
        show_pagination_controls = st.session_state.page_size != "Todos"
        
        if show_pagination_controls:
            st.markdown(
                f"<p style='text-align: center; margin-bottom: 2px;'>Página <b>{st.session_state.page}</b> de <b>{total_pages}</b> | Total de <b>{st.session_state.total_rows:,}</b> linhas</p>",
                unsafe_allow_html=True
            )
        else:
            total_filtered = len(df_filtered) 
            st.markdown(
                f"<p style='text-align: center; margin-bottom: 2px;'>Exibindo <b>{total_filtered:,}</b> linhas filtradas (Todos)</p>",
                unsafe_allow_html=True
            )

        col1, col2, col3, col4 = st.columns([1.5, 2, 2, 1.5]) 

        # Botão Anterior
        with col1:
            if st.button("⬅ Anterior", disabled=(st.session_state.page <= 1) or not show_pagination_controls, use_container_width=True):
                change_page(-1)
                st.rerun()

        # Input "Ir para pág."
        with col2:
            page_input = st.number_input(
                "Ir para pág.",
                min_value=1,
                max_value=max(1, total_pages),
                value=st.session_state.page,
                step=1,
                key="page_input",
                label_visibility="hidden",
                disabled=not show_pagination_controls
            )
            st.caption("Ir para pág.")

            if show_pagination_controls and (st.session_state.page_input != st.session_state.page):
                st.session_state.page = page_input
                st.rerun()

        # Select "Itens por pág."
        with col3:
            page_size_options = [25, 50, 100, 250, 500, 1000, 5000, "Todos"]
            
            if st.session_state.page_size not in page_size_options:
                page_size_options.append(st.session_state.page_size)
                page_size_options.sort(key=lambda x: (isinstance(x, str), x))
                
            current_index = page_size_options.index(st.session_state.page_size)
            
            new_page_size = st.selectbox(
                "Itens por pág.",
                page_size_options,
                index=current_index,
                key="page_size_selector",
                label_visibility="hidden"
            )
            st.caption("Itens por pág.")
            
            if new_page_size != st.session_state.page_size:
                st.session_state.page_size = new_page_size
                st.session_state.page = 1
                st.rerun()

        # Botão Próximo
        with col4:
            if isinstance(st.session_state.page_size, int):
                has_more = len(df) == st.session_state.page_size
            else:
                has_more = False
                
            is_last_page = st.session_state.page >= total_pages
            
            if st.button("Próximo ➡", disabled=(not has_more or is_last_page or not show_pagination_controls), use_container_width=True):
                change_page(1)
                st.rerun()

        # Download
        
        st.divider()
        
        pdf_bytes = dataframe_to_pdf_bytes(df_filtered)
        
        # Gera um PDF absurdo mas é um PDF
        st.download_button(
            label="📥 Baixar esta página filtrada como PDF",
            data=pdf_bytes,
            file_name=f"{TABLE_NAME}_pagina_{st.session_state.page}_filtrada.pdf",
            mime="application/pdf",
            use_container_width=True
        )

except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.code(f"""
    Verifique:
    - Tabela '{TABLE_NAME}' existe?
    - Banco está rodando em {DB_HOST}:{DB_PORT}?
    - Credenciais corretas?
    """)