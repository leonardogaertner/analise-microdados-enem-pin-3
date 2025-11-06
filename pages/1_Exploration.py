import streamlit as st
import os
import pandas as pd
from sqlalchemy import create_engine
import numpy as np
from fpdf import FPDF
from Exploration import column_config

# --- AJUSTE ADICIONADO ---
# Define o layout da página como "wide"
# Esta deve ser a PRIMEIRA chamada st.* no script
st.set_page_config(layout="wide")
# -------------------------

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

# --- Funções de Dados e Filtro Refatoradas ---

@st.cache_data(ttl=3600)
def get_filter_metadata(table_name):
    """
    Busca os metadados (min, max, valores únicos) de TODAS as colunas
    diretamente do banco de dados para popular os filtros corretamente.
    """
    engine = get_engine()
    
    # Gera o mapping reverso (Nome Amigável -> Nome no BD UPPERCASE)
    # Ex: {'Cód. Município Escola': 'CO_MUNICIPIO_ESC'}
    reverse_mapping = {v: k for k, v in column_config.COLUMN_MAPPING.items()}

    # Carrega um sample para inferir tipos e colunas
    # (Nomes de colunas aqui são MAIÚSCULOS, ex: "CO_MUNICIPIO_ESC")
    try:
        df_sample_orig = pd.read_sql(f'SELECT * FROM "{table_name}" LIMIT 5', engine)
    except Exception as e:
        st.error(f"Não foi possível carregar o schema da tabela '{table_name}': {e}")
        return None, None, None

    # Cria um df sample com nomes mapeados para inferência de tipo
    df_sample_mapped = df_sample_orig.copy()
    
    # Garante que as colunas estejam em MAIÚSCULO para bater com o MAPPING
    df_sample_mapped.columns = df_sample_mapped.columns.str.upper() 
    
    # Renomeia (ex: "CO_MUNICIPIO_ESC" -> "Cód. Município Escola")
    df_sample_mapped = df_sample_mapped.rename(columns=column_config.COLUMN_MAPPING)
    
    metadata = {}
    # Lista de colunas mapeadas (amigáveis) e não mapeadas (originais)
    all_mapped_columns = list(df_sample_mapped.columns)
    
    with st.spinner("Carregando metadados para filtros... (só na 1ª vez)"):
        for mapped_column in all_mapped_columns:
            
            # Busca o nome original (MAIÚSCULO)
            original_col_key = reverse_mapping.get(mapped_column) # Ex: 'CO_MUNICIPIO_ESC'
            
            if original_col_key:
                original_col = original_col_key
            else:
                # Fallback: assume que o nome mapeado é o nome da coluna original
                original_col = mapped_column

            # Valida se o nome da coluna (MAIÚSCULO) realmente existe no sample original
            if original_col not in df_sample_orig.columns:
                st.warning(f"Não foi possível encontrar a coluna original '{original_col}' (mapeada de '{mapped_column}'). Pulando filtro.")
                col_info = {'type': 'unsupported'}
                metadata[mapped_column] = col_info
                continue

            col_info = {}
            try:
                dtype = df_sample_mapped.dtypes[mapped_column]
                
                # --- INÍCIO DA CORREÇÃO ---
                # A lógica foi invertida. Primeiro checamos se é uma coluna 'CÓD.'
                # pelo nome, independentemente do tipo de dado (numérico ou texto).
                
                if mapped_column.upper().startswith('CÓD.'):
                    unique_vals_df = pd.read_sql(f'SELECT DISTINCT "{original_col}" FROM "{table_name}" WHERE "{original_col}" IS NOT NULL ORDER BY "{original_col}" ASC LIMIT 1000', engine)
                    col_info['type'] = 'code'
                    
                    # Tenta converter os valores para int (para o placeholder)
                    # mas não falha se não conseguir (ex: se o código for 'SP')
                    options_int = []
                    for v in unique_vals_df.iloc[:, 0].dropna().unique():
                        try:
                            options_int.append(int(v))
                        except (ValueError, TypeError):
                            pass # Ignora valores não-numéricos
                    
                    col_info['options'] = sorted(options_int)

                # Se não for 'CÓD.', continuamos com a lógica de tipos
                elif pd.api.types.is_numeric_dtype(dtype):
                    # Esta parte agora só executa se NÃO for uma coluna 'CÓD.'
                    min_max_df = pd.read_sql(f'SELECT MIN("{original_col}"), MAX("{original_col}") FROM "{table_name}"', engine)
                    col_info['type'] = 'numeric'
                    col_info['min'] = int(np.floor(min_max_df.iloc[0, 0] if pd.notnull(min_max_df.iloc[0, 0]) else 0))
                    col_info['max'] = int(np.ceil(min_max_df.iloc[0, 1] if pd.notnull(min_max_df.iloc[0, 1]) else 0))
                
                elif pd.api.types.is_datetime64_any_dtype(dtype):
                    min_max_df = pd.read_sql(f'SELECT MIN("{original_col}"), MAX("{original_col}") FROM "{table_name}" WHERE "{original_col}" IS NOT NULL', engine)
                    col_info['type'] = 'datetime'
                    col_info['min'] = min_max_df.iloc[0, 0]
                    col_info['max'] = min_max_df.iloc[0, 1]

                elif pd.api.types.is_object_dtype(dtype) or pd.api.types.is_categorical_dtype(dtype):
                    # Esta parte agora só executa se NÃO começar com 'CÓD.'
                    unique_vals_df = pd.read_sql(f'SELECT DISTINCT "{original_col}" FROM "{table_name}" WHERE "{original_col}" IS NOT NULL ORDER BY "{original_col}" ASC LIMIT 1000', engine)
                    col_info['type'] = 'categorical'
                    col_info['options'] = unique_vals_df.iloc[:, 0].dropna().unique()
                
                else:
                    col_info['type'] = 'unsupported'
                
                # --- FIM DA CORREÇÃO ---

            except Exception as e:
                st.warning(f"Não foi possível carregar metadados para filtro da coluna '{mapped_column}' ({original_col}): {e}")
                col_info['type'] = 'unsupported'

            metadata[mapped_column] = col_info
            
    # Retorna o reverse_mapping junto
    return metadata, all_mapped_columns, reverse_mapping

def tratar_filtro_codigo(column: str, st_column_object, key_prefix: str, metadata: dict) -> None:
    """
    Cria um filtro de *digitação* (st.text_input) para colunas de código.
    Permite que o usuário digite múltiplos valores separados por vírgula.
    """
    unique_values = metadata.get('options', [])
    placeholder_text = f"Ex: {unique_values[0]}" if unique_values else "Digite códigos, ex: 11, 35, 53"
    
    # Chave para o campo de texto (onde o usuário digita)
    text_key = f"text_{key_prefix}"
    
    # Chave para a lista processada (que o 'build_query' usa)
    list_key = f"multi_{key_prefix}"

    # Callback que será chamada QUANDO o usuário pressionar Enter no text_input
    def process_text_and_reset_page():
        # 1. Ler o valor do campo de texto
        raw_text = st.session_state.get(text_key, "")
        
        if not raw_text:
            st.session_state[list_key] = []
        else:
            # 2. Processar o texto (separar por vírgula, limpar, converter p/ int)
            values = [val.strip() for val in raw_text.split(',') if val.strip()]
            processed_values = []
            for v in values:
                try:
                    # A metadata original convertia para int
                    processed_values.append(int(v))
                except ValueError:
                    # Se o usuário digitar algo não-numérico, ignora
                    pass 
            
            # 3. Salvar a lista processada na 'key' que a query espera
            st.session_state[list_key] = processed_values
        
        # 4. Resetar a página (como os outros filtros fazem)
        st.session_state.page = 1

    # --- Lógica de Sincronização ---
    # Isso garante que o campo de texto e a lista de filtros
    # permaneçam sincronizados, especialmente após "Limpar Filtros"

    current_list_value = st.session_state.get(list_key, [])
    current_text_value = st.session_state.get(text_key, "")
    
    # Converte a lista atual (ex: [11, 35]) de volta para texto (ex: "11, 35")
    text_from_list = ", ".join(map(str, current_list_value))

    # Se o botão "Limpar Filtros" foi pressionado:
    # A list_key é limpa (ex: "multi_..."), mas a text_key (ex: "text_...") não.
    # Precisamos forçar a text_key a limpar também.
    if not current_list_value and current_text_value:
        st.session_state[text_key] = ""
        current_text_value = "" # Atualiza a variável local
    
    # Se o estado de lista (text_from_list) for diferente do estado de texto
    # (o que pode acontecer em recarregamentos), sincronize-os.
    elif text_from_list != current_text_value:
        st.session_state[text_key] = text_from_list
        current_text_value = text_from_list

    # --- Fim da Sincronização ---

    st_column_object.text_input(
        f"Digite os valores de {column} (separados por vírgula)",
        key=text_key,
        placeholder=placeholder_text,
        on_change=process_text_and_reset_page,
        # O valor default é controlado pela lógica de sincronização acima
    )

def render_filter_widgets(table_name: str, metadata: dict, all_columns: list):
    """
    Renderiza os widgets de filtro com base nos metadados.
    """
    st.markdown("### 🔎 Filtros")

    col_toggle, col_clear = st.columns([1, 3])

    if "filters_active" not in st.session_state:
        st.session_state.filters_active = False

    def reset_page():
        st.session_state.page = 1
        
    modify = col_toggle.checkbox(
        f"Ativar filtros",
        value=st.session_state.filters_active,
        key=f"filter_checkbox_{table_name}",
        on_change=reset_page
    )

    if col_clear.button("🔁 Limpar filtros", key=f"clear_filters_{table_name}"):
        keys_to_delete = []
        for key in list(st.session_state.keys()):
            if key.startswith(f"{table_name}_") or \
               key.startswith(f"filter_") or \
               key.startswith("multi_") or \
               key.startswith("slider_") or \
               key.startswith("date_") or \
               key.startswith("text_"):
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del st.session_state[key]
        
        # Desmarca a flag que ativa os filtros
        st.session_state.filters_active = False
        st.session_state[f"filter_checkbox_{table_name}"] = False

        #Recarrega a tabela sem os filtros aplicados
        st.session_state.page = 1
        st.rerun()

    st.session_state.filters_active = modify

    if not modify:
        return

    to_filter_columns = st.multiselect(
        "Selecione colunas para filtrar:",
        all_columns,
        key=f"filter_columns_{table_name}",
        on_change=reset_page
    )

    for column in to_filter_columns:
        col1, col2 = st.columns((0.01, 4))
        key_prefix = f"{table_name}_{column}"
        
        col_info = metadata.get(column, {'type': 'unsupported'})

        if col_info['type'] == 'unsupported':
             # O aviso já foi dado em get_filter_metadata
            continue
        
        if col_info['type'] == 'code':
            tratar_filtro_codigo(column, col2, key_prefix, col_info)
        
        elif col_info['type'] == 'numeric':
            _min = col_info.get('min', 0)
            _max = col_info.get('max', 1)

            if _min == _max:
                col2.info(f"ℹ️ Coluna '{column}' contém apenas um valor ({_min}).")
                continue

            col2.slider(
                f"Faixa de {column}",
                min_value=_min,
                max_value=_max,
                value=st.session_state.get(f"slider_{key_prefix}", (_min, _max)),
                key=f"slider_{key_prefix}",
                on_change=reset_page
            )

        elif col_info['type'] == 'datetime':
            _min = col_info.get('min')
            _max = col_info.get('max')
            
            if not _min or not _max:
                col2.info(f"⚠️ Coluna '{column}' não possui datas válidas.")
                continue
                
            col2.date_input(
                f"Intervalo de {column}",
                value=st.session_state.get(f"date_{key_prefix}", (_min, _max)),
                key=f"date_{key_prefix}",
                min_value=_min,
                max_value=_max,
                on_change=reset_page
            )

        elif col_info['type'] == 'categorical':
            unique_values = col_info.get('options', [])
            if len(unique_values) == 0:
                col2.info(f"⚠️ Coluna '{column}' sem valores válidos para seleção.")
                continue
            
            col2.multiselect(
                f"Valores de {column}",
                unique_values,
                key=f"multi_{key_prefix}",
                on_change=reset_page
            )
        
        else:
             col2.warning(f"Tipo de dado da coluna '{column}' não é suportado para filtragem.")

def build_query_and_params(table_name, page, page_size, metadata, all_columns, reverse_mapping):
    """
    Constrói a query SQL (dados e contagem) e os parâmetros
    com base nos filtros ativos no st.session_state.
    """
    
    base_query = f'SELECT * FROM "{table_name}"'
    count_query = f'SELECT COUNT(*) FROM "{table_name}"'
    
    where_clauses = []
    params = {} 

    if st.session_state.get("filters_active", False):
        to_filter_columns = st.session_state.get(f"filter_columns_{table_name}", [])
        
        for column in to_filter_columns:
            if column not in metadata: continue 

            key_prefix = f"{table_name}_{column}"
            col_info = metadata[column]
            
            if col_info['type'] == 'unsupported':
                continue

            original_col_key = reverse_mapping.get(column)
            
            if original_col_key:
                original_col_name = original_col_key
            else:
                original_col_name = column

            if col_info['type'] == 'numeric' or col_info['type'] == 'datetime':
                key = f"slider_{key_prefix}" if col_info['type'] == 'numeric' else f"date_{key_prefix}"
                
                if key in st.session_state:
                    val = st.session_state[key]
                    if isinstance(val, tuple) and len(val) == 2:
                        user_min, user_max = val
                        if user_min != col_info['min'] or user_max != col_info['max']:
                            param_min = f'p_min_{original_col_name}'
                            param_max = f'p_max_{original_col_name}'
                            where_clauses.append(f'"{original_col_name}" BETWEEN %({param_min})s AND %({param_max})s')
                            params[param_min] = user_min
                            params[param_max] = user_max
            
            elif col_info['type'] == 'code' or col_info['type'] == 'categorical':
                key = f"multi_{key_prefix}"
                if key in st.session_state:
                    selected_values = st.session_state[key]
                    if selected_values:
                        param_names = [f'p_val_{original_col_name}_{i}' for i in range(len(selected_values))]
                        where_clauses.append(f'"{original_col_name}" IN ({", ".join([f"%({p})s" for p in param_names])})')
                        for p_name, val in zip(param_names, selected_values):
                            params[p_name] = val
    
    if where_clauses:
        where_string = " WHERE " + " AND ".join(where_clauses)
        base_query += where_string
        count_query += where_string

    if page_size == "Todos":
        final_query = base_query + ";"
    else:
        offset = (page - 1) * page_size
        final_query = base_query + f" LIMIT %(limit)s OFFSET %(offset)s;"
        params['limit'] = page_size
        params['offset'] = offset

    return final_query, count_query, params

@st.cache_data(ttl=3600)
def load_paginated_data(query, params_tuple):
    """
    Executa a query de busca de dados.
    """
    engine = get_engine()
    params = dict(params_tuple)
    try:
        return pd.read_sql(query, engine, params=params)
    except Exception as e:
        st.error(f"Erro ao executar a query de dados: {e}")
        st.code(query)
        st.code(params)
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_filtered_row_count(count_query, params_tuple):
    """
    Executa a query de contagem de linhas filtradas.
    """
    engine = get_engine()
    params = dict(params_tuple)
    try:
        return pd.read_sql(count_query, engine, params=params).iloc[0, 0]
    except Exception as e:
        st.error(f"Erro ao executar a query de contagem: {e}")
        st.code(count_query)
        st.code(params)
        return 0

# Função para criar o PDF (sem alterações)
def dataframe_to_pdf_bytes(df: pd.DataFrame) -> bytes:
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_font("Arial", size=8) 
    df_str = df.fillna('N/A').astype(str)
    num_cols = len(df_str.columns)
    page_width = pdf.w - 2 * pdf.l_margin
    col_width = page_width / num_cols
    line_height = pdf.font_size * 2
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


# --- Bloco Principal de Execução ---

TABLE_NAME = "dados_enem_consolidado"
try:
    # 1. Carregar Metadados
    metadata, all_columns, reverse_mapping = get_filter_metadata(TABLE_NAME)
    
    if metadata is None:
        raise Exception("Não foi possível carregar os metadados da tabela.")

    # 2. Renderizar os widgets de filtro
    render_filter_widgets(TABLE_NAME, metadata, all_columns)

    # 3. Construir as queries
    query, count_query, params = build_query_and_params(
        TABLE_NAME, 
        st.session_state.page, 
        st.session_state.page_size,
        metadata,
        all_columns,
        reverse_mapping
    )
    
    # 4. Criar tuples hasheáveis para o cache
    count_params_tuple = tuple(sorted(p for p in params.items() if p[0] not in ('limit', 'offset')))
    data_params_tuple = tuple(sorted(params.items()))


    # 5. Executar a query de contagem
    with st.spinner("Carregando total de registros..."):
        total_rows = get_filtered_row_count(count_query, count_params_tuple)
        st.session_state.total_rows = total_rows

    # 6. Executar a query de dados
    with st.spinner(f"Carregando página {st.session_state.page}..."):
        df = load_paginated_data(query, data_params_tuple)
    
    # 7. Renomear colunas (para exibição)
    if not df.empty:
        df = df.rename(columns=column_config.COLUMN_MAPPING)

    if df.empty:
        st.warning("Nenhum dado encontrado com estes filtros e paginação.")
    else:
        
        # --- INÍCIO DA MODIFICAÇÃO (SELETOR DE COLUNAS) ---

        # Pega todas as colunas (já com nomes amigáveis)
        all_available_columns = list(df.columns)

        # <-- MODIFIQUE AQUI!
        # Defina a lista de colunas que você quer exibir por padrão.
        # Use os nomes AMIGÁVEIS (ex: "Cód. Município Escola")
        DEFAULT_COLUMNS = [
            "Ano", 
            "Média Geral"
        ]

        # Garante que as colunas padrão realmente existem neste dataframe
        # (para evitar erros caso a query mude)
        default_safe = [col for col in DEFAULT_COLUMNS if col in all_available_columns]

        # Se a lista 'default_safe' ficar vazia por algum motivo, 
        # mostre as 5 primeiras colunas como um fallback.
        if not default_safe and all_available_columns:
            default_safe = all_available_columns[:5]

        st.markdown("#### 📊 Seleção de Colunas")
        
        # Cria o seletor de colunas para o usuário
        selected_cols = st.multiselect(
            "Selecione as colunas para exibir:",
            options=all_available_columns,
            default=default_safe,
            key="column_selector"
        )
        
        # --- FIM DA MODIFICAÇÃO ---
        
        
        # 8. Exibir dataframe com colunas selecionadas
        if selected_cols:
            st.dataframe(df[selected_cols], use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma coluna selecionada para exibição.")
        
        # Paginação
        if st.session_state.page_size == "Todos":
            total_pages = 1
        else:
            total_pages = (st.session_state.total_rows + st.session_state.page_size - 1) // st.session_state.page_size
            
        show_pagination_controls = st.session_state.page_size != "Todos"
        
        if show_pagination_controls:
            st.markdown(
                f"<p style='text-align: center; margin-bottom: 2px;'>Página <b>{st.session_state.page}</b> de <b>{total_pages if total_pages > 0 else 1}</b> | Total de <b>{st.session_state.total_rows:,}</b> linhas filtradas</p>",
                unsafe_allow_html=True
            )
        else:
            total_filtered = len(df)
            st.markdown(
                f"<p style='text-align: center; margin-bottom: 2px;'>Exibindo <b>{total_filtered:,}</b> linhas filtradas (Todos)</p>",
                unsafe_allow_html=True
            )

        col1, col2, col3, col4 = st.columns([1.5, 2, 2, 1.5]) 

        with col1:
            if st.button("⬅ Anterior", disabled=(st.session_state.page <= 1) or not show_pagination_controls, use_container_width=True):
                change_page(-1)
                st.rerun()

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

        with col4:
            is_last_page = st.session_state.page >= total_pages
            
            if st.button("Próximo ➡", disabled=(is_last_page or not show_pagination_controls), use_container_width=True):
                change_page(1)
                st.rerun()
        
        st.divider()
        
        # Modificação: Passar o dataframe filtrado (df[selected_cols]) para o PDF
        # Se você quiser que o PDF sempre contenha TODAS as colunas, 
        # mantenha a linha original: pdf_bytes = dataframe_to_pdf_bytes(df)
        
        if selected_cols:
            pdf_bytes = dataframe_to_pdf_bytes(df[selected_cols])
            
            st.download_button(
                label="📥 Baixar esta página (filtrada e colunas selecionadas) como PDF",
                data=pdf_bytes,
                file_name=f"{TABLE_NAME}_pagina_{st.session_state.page}_filtrada.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        else:
            st.warning("Selecione pelo menos uma coluna para gerar o PDF.")


except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.exception(e) 
    st.code(f"""
    Verifique:
    - Tabela '{TABLE_NAME}' existe?
    - Banco está rodando em {DB_HOST}:{DB_PORT}?
    - Credenciais corretas?
    - Mapeamento de colunas em 'column_config.py' está correto? (As chaves devem ser MAIÚSCULAS)
    """)