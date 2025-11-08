import streamlit as st
import pandas as pd
import numpy as np
from . import column_config as cc
from .db_utils import get_engine, TABLE_NAME

# ===================================================================
# (get_filter_metadata e tratar_filtro_codigo NÃO MUDARAM)
# Cole suas versões existentes aqui.
# ===================================================================

@st.cache_data(ttl=3600)
def get_filter_metadata():
    """ (Sem alterações) """
    engine = get_engine()
    reverse_mapping = {v: k for k, v in cc.COLUMN_MAPPING.items()}
    try:
        df_sample_orig = pd.read_sql(f'SELECT * FROM "{TABLE_NAME}" LIMIT 5', engine)
    except Exception as e:
        st.error(f"Não foi possível carregar o schema da tabela '{TABLE_NAME}': {e}")
        return None, None, None
    df_sample_mapped = df_sample_orig.copy()
    df_sample_mapped.columns = df_sample_mapped.columns.str.upper()
    df_sample_mapped = df_sample_mapped.rename(columns=cc.COLUMN_MAPPING)
    metadata = {}
    all_mapped_columns = list(df_sample_mapped.columns)
    with st.spinner("Carregando metadados para filtros... (só na 1ª vez)"):
        for mapped_column in all_mapped_columns:
            original_col_key = reverse_mapping.get(mapped_column)
            if not original_col_key or original_col_key not in df_sample_orig.columns:
                col_info = {'type': 'unsupported'}
                metadata[mapped_column] = col_info
                continue
            original_col = original_col_key
            col_info = {}
            try:
                dtype = df_sample_mapped.dtypes[mapped_column]
                if mapped_column.upper().startswith('CÓD.'):
                    unique_vals_df = pd.read_sql(f'SELECT DISTINCT "{original_col}" FROM "{TABLE_NAME}" WHERE "{original_col}" IS NOT NULL ORDER BY "{original_col}" ASC LIMIT 1000', engine)
                    col_info['type'] = 'code'
                    options_int = []
                    for v in unique_vals_df.iloc[:, 0].dropna().unique():
                        try:
                            options_int.append(int(v))
                        except (ValueError, TypeError): pass
                    col_info['options'] = sorted(options_int)
                elif pd.api.types.is_numeric_dtype(dtype):
                    min_max_df = pd.read_sql(f'SELECT MIN("{original_col}"), MAX("{original_col}") FROM "{TABLE_NAME}"', engine)
                    col_info['type'] = 'numeric'
                    col_info['min'] = int(np.floor(min_max_df.iloc[0, 0] if pd.notnull(min_max_df.iloc[0, 0]) else 0))
                    col_info['max'] = int(np.ceil(min_max_df.iloc[0, 1] if pd.notnull(min_max_df.iloc[0, 1]) else 0))
                elif pd.api.types.is_datetime64_any_dtype(dtype):
                    min_max_df = pd.read_sql(f'SELECT MIN("{original_col}"), MAX("{original_col}") FROM "{TABLE_NAME}" WHERE "{original_col}" IS NOT NULL', engine)
                    col_info['type'] = 'datetime'
                    col_info['min'] = min_max_df.iloc[0, 0]
                    col_info['max'] = min_max_df.iloc[0, 1]
                elif pd.api.types.is_object_dtype(dtype) or pd.api.types.is_categorical_dtype(dtype):
                    unique_vals_df = pd.read_sql(f'SELECT DISTINCT "{original_col}" FROM "{TABLE_NAME}" WHERE "{original_col}" IS NOT NULL ORDER BY "{original_col}" ASC LIMIT 1000', engine)
                    col_info['type'] = 'categorical'
                    col_info['options'] = unique_vals_df.iloc[:, 0].dropna().unique()
                else:
                    col_info['type'] = 'unsupported'
            except Exception as e:
                st.warning(f"Não foi possível carregar metadados para '{mapped_column}': {e}")
                col_info['type'] = 'unsupported'
            metadata[mapped_column] = col_info
    return metadata, all_mapped_columns, reverse_mapping

def tratar_filtro_codigo(column: str, st_column_object, key_prefix: str, metadata: dict) -> None:
    """ (Sem alterações) """
    unique_values = metadata.get('options', [])
    placeholder_text = f"Ex: {unique_values[0]}" if unique_values else "Digite códigos, ex: 11, 35, 53"
    text_key = f"text_{key_prefix}"
    list_key = f"multi_{key_prefix}"
    def process_text_and_reset_page():
        raw_text = st.session_state.get(text_key, "")
        if not raw_text:
            st.session_state[list_key] = []
        else:
            values = [val.strip() for val in raw_text.split(',') if val.strip()]
            processed_values = []
            for v in values:
                try:
                    processed_values.append(int(v))
                except ValueError:
                    pass 
            st.session_state[list_key] = processed_values
        if 'page' in st.session_state:
            st.session_state.page = 1
    current_list_value = st.session_state.get(list_key, [])
    current_text_value = st.session_state.get(text_key, "")
    text_from_list = ", ".join(map(str, current_list_value))
    if not current_list_value and current_text_value:
        st.session_state[text_key] = ""
        current_text_value = ""
    elif text_from_list != current_text_value:
        st.session_state[text_key] = text_from_list
        current_text_value = text_from_list
    st_column_object.text_input(
        f"Digite os valores de {column} (separados por vírgula)",
        key=text_key,
        placeholder=placeholder_text,
        on_change=process_text_and_reset_page,
    )

# ===================================================================
# FUNÇÃO 'render_filter_widgets' (CORRIGIDA)
# ===================================================================
def render_filter_widgets(metadata: dict, all_columns: list, container=st, unique_prefix="default"):
    """
    Renderiza os widgets de filtro dentro do 'container' especificado,
    usando um 'unique_prefix' para o session_state.
    """
    container.markdown("### 🔎 Filtros")
    col_toggle, col_clear = container.columns([1, 1])

    # --- CORREÇÃO ---
    # Simplificado para usar UMA chave de estado por prefixo
    active_key = f"{unique_prefix}_filters_active"
    
    # Inicializa a chave de estado se ela não existir
    if active_key not in st.session_state:
        st.session_state[active_key] = False
    # --- FIM DA CORREÇÃO ---

    def reset_page_filter():
        if 'page' in st.session_state and unique_prefix == "data":
            st.session_state.page = 1
        
    # --- CORREÇÃO ---
    # O widget da checkbox agora lê e escreve DIRETAMENTE
    # na chave de estado 'active_key'.
    # O 'value' foi removido para evitar conflitos.
    modify = col_toggle.checkbox(
        f"Ativar filtros",
        key=active_key, # A chave é a fonte da verdade
        on_change=reset_page_filter
    )
    # --- FIM DA CORREÇÃO ---

    if col_clear.button("🔁 Limpar filtros", key=f"{unique_prefix}_clear_filters"):
        keys_to_delete = [k for k in st.session_state.keys() if k.startswith(f"{unique_prefix}_")]
        
        for key in keys_to_delete:
            if key in st.session_state:
                del st.session_state[key]
        
        # --- CORREÇÃO ---
        # Reseta a chave de estado principal
        st.session_state[active_key] = False
        # --- FIM DA CORREÇÃO ---
        
        if 'page' in st.session_state and unique_prefix == "data":
            st.session_state.page = 1
        st.rerun()

    # --- CORREÇÃO ---
    # A linha 'st.session_state[filter_active_key] = modify' foi removida.
    # Ela era redundante e causava o bug.
    # A variável 'modify' agora reflete o estado real da checkbox.
    # --- FIM DA CORREÇÃO ---
    
    if not modify:
        return # Esta guarda agora funciona corretamente

    # O resto da função (multiselect, sliders, etc.) não mudou,
    # mas agora será executado quando 'modify' for True.
    filter_columns_key = f"{unique_prefix}_filter_columns"
    to_filter_columns = container.multiselect(
        "Selecione colunas para filtrar:",
        all_columns,
        key=filter_columns_key,
        on_change=reset_page_filter
    )

    for column in to_filter_columns:
        key_prefix = f"{unique_prefix}_{column}" 
        col_info = metadata.get(column, {'type': 'unsupported'})
        
        widget_container = container

        if col_info['type'] == 'unsupported': continue
        
        if col_info['type'] == 'code':
            tratar_filtro_codigo(column, widget_container, key_prefix, col_info)
        
        elif col_info['type'] == 'numeric':
            _min, _max = col_info.get('min', 0), col_info.get('max', 1)
            if _min == _max: continue
            widget_container.slider(
                f"Faixa de {column}", min_value=_min, max_value=_max,
                value=st.session_state.get(f"slider_{key_prefix}", (_min, _max)),
                key=f"slider_{key_prefix}", on_change=reset_page_filter
            )
        elif col_info['type'] == 'datetime':
            _min, _max = col_info.get('min'), col_info.get('max')
            if not _min or not _max: continue
            widget_container.date_input(
                f"Intervalo de {column}",
                value=st.session_state.get(f"date_{key_prefix}", (_min, _max)),
                key=f"date_{key_prefix}", min_value=_min, max_value=_max,
                on_change=reset_page_filter
            )
        elif col_info['type'] == 'categorical':
            unique_values = col_info.get('options', [])
            if len(unique_values) == 0: continue
            widget_container.multiselect(
                f"Valores de {column}",
                unique_values, key=f"multi_{key_prefix}", on_change=reset_page_filter
            )
        else:
             widget_container.warning(f"Tipo '{column}' não suportado.")

# ===================================================================
# FUNÇÃO 'build_query_and_params' (CORRIGIDA)
# ===================================================================
def build_query_and_params(metadata: dict, reverse_mapping: dict, enable_pagination: bool = True, unique_prefix="default"):
    """
    Constrói a query SQL (dados e contagem) e os parâmetros
    com base nos filtros ativos (usando 'unique_prefix').
    """
    
    base_query = f'SELECT * FROM "{TABLE_NAME}"'
    count_query = f'SELECT COUNT(*) FROM "{TABLE_NAME}"'
    
    where_clauses = []
    params = {} 

    # --- CORREÇÃO ---
    # Lê o estado do filtro da MESMA chave que a checkbox usa
    active_key = f"{unique_prefix}_filters_active"
    if st.session_state.get(active_key, False):
    # --- FIM DA CORREÇÃO ---
    
        to_filter_columns = st.session_state.get(f"{unique_prefix}_filter_columns", [])
        
        for column in to_filter_columns:
            if column not in metadata: continue 

            key_prefix = f"{unique_prefix}_{column}"
            col_info = metadata[column]
            if col_info['type'] == 'unsupported': continue

            original_col_key = reverse_mapping.get(column)
            if not original_col_key: continue
            original_col_name = original_col_key

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

    if enable_pagination:
        page_size = st.session_state.get('page_size', 100)
        page = st.session_state.get('page', 1)
        if page_size == "Todos":
            final_query = base_query + " ORDER BY 1;"
        else:
            offset = (page - 1) * page_size
            final_query = base_query + f" ORDER BY 1 LIMIT %(limit)s OFFSET %(offset)s;"
            params['limit'] = page_size
            params['offset'] = offset
    else:
        final_query = base_query + ";"

    return final_query, count_query, params