import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
import numpy as np
import altair as alt

# Importa os módulos refatorados
try:
    from Exploration import column_config as cc
    from Exploration.db_utils import get_engine, TABLE_NAME
    from Exploration.filter_utils import (
        get_filter_metadata, 
        render_filter_widgets, 
        build_query_and_params
    )
    from Exploration import graph_utils as gu
    from Exploration.pdf_utils import dataframe_to_pdf_bytes

except ImportError:
    st.error("Erro ao carregar módulos. Verifique a estrutura de pastas 'Exploration'.")
    st.stop()

# --- INICIALIZAÇÃO OBRIGATÓRIA ---
if 'page' not in st.session_state:
    st.session_state.page = 1
if 'page_size' not in st.session_state:
    st.session_state.page_size = 100
# ------------------------------------

st.set_page_config(layout="wide")

# (Seu CSS e botão "Voltar" permanecem aqui)
# st.markdown(""" ... (seu CSS) ... """)
if st.button("Voltar", key="back_button"):
    st.switch_page("app.py")

st.title("Exploração e Visualização dos Dados")

# ===================================================================
# FUNÇÕES DE CARREGAMENTO DE DADOS
# ===================================================================

def change_page(delta):
    st.session_state.page = max(1, st.session_state.page + delta)

@st.cache_data(ttl=3600)
def load_cached_metadata():
    """
    Função wrapper para carregar e cachear os metadados uma única vez.
    Chama a função 'get_filter_metadata' importada.
    """
    metadata, all_columns, reverse_mapping = get_filter_metadata()
    if metadata is None:
        raise Exception("Não foi possível carregar os metadados da tabela. (get_filter_metadata retornou None)")
    return metadata, all_columns, reverse_mapping

@st.cache_data(ttl=3600)
def load_paginated_data(query, params_tuple):
    engine = get_engine()
    params = dict(params_tuple)
    try:
        return pd.read_sql(query, engine, params=params)
    except Exception as e:
        st.error(f"Erro ao executar a query de dados: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_filtered_row_count(count_query, params_tuple):
    engine = get_engine()
    params = dict(params_tuple)
    try:
        return pd.read_sql(count_query, engine, params=params).iloc[0, 0]
    except Exception as e:
        st.error(f"Erro ao executar a query de contagem: {e}")
        return 0

@st.cache_data(ttl=3600)
def load_graph_data(columns: list, query_tuple: tuple, params_tuple: tuple, reverse_mapping: dict):
    engine = get_engine()
    base_query = query_tuple[0]
    params = dict(params_tuple)
    db_cols = []
    for col in columns:
        db_col = reverse_mapping.get(col)
        if db_col:
            db_cols.append(f'"{db_col}"')
        else:
            fallback_col = [k for k, v in cc.COLUMN_MAPPING.items() if v == col]
            if fallback_col:
                db_cols.append(f'"{fallback_col[0]}"')
            else:
                st.warning(f"Coluna '{col}' não encontrada no mapeamento. Será ignorada.")
            
    if not db_cols:
        st.error("Nenhuma coluna válida selecionada.")
        return pd.DataFrame()

    query = base_query.replace('SELECT *', f'SELECT {", ".join(db_cols)}')
    
    try:
        df = pd.read_sql_query(query, engine, params=params)
        if len(df) > 100000:
            st.info(f"Dados filtrados ({len(df):,} linhas) são muito grandes. Exibindo amostra de 100.000 linhas.")
            df = df.sample(100000, random_state=1)
        df.columns = df.columns.str.upper()
        df = df.rename(columns=cc.COLUMN_MAPPING)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados para o gráfico: {e}")
        st.code(query)
        st.code(params)
        return pd.DataFrame()

# ===================================================================
# BLOCO PRINCIPAL DE EXECUÇÃO
# ===================================================================

TABLE_NAME = "dados_enem_consolidado" 
try:
    # 1. Carregar Metadados (FEITO UMA VEZ)
    metadata, all_columns, reverse_mapping = load_cached_metadata() 

    # 2. Criar Abas
    tab_dados, tab_graficos = st.tabs(["📊 Tabela de Dados", "📈 Construtor de Gráficos"])

    # ======================================================
    # ABA 1: TABELA DE DADOS
    # ======================================================
    with tab_dados:
        st.header("Explorar Dados da Tabela")
        
        # 3a. Renderizar filtros para a TABELA
        # (Renderiza no container 'st', usa prefixo 'data')
        
        # --- AJUSTE 1 AQUI ---
        # container=st mudado para container=tab_dados
        render_filter_widgets(metadata, all_columns, container=tab_dados, unique_prefix="data")
        st.divider()

        # 4a. Construir as queries para PAGINAÇÃO
        query_paginada, count_query, params_paginados = build_query_and_params(
            metadata=metadata,
            reverse_mapping=reverse_mapping,
            enable_pagination=True,
            unique_prefix="data"  # Usa o prefixo 'data'
        )

        count_params_tuple = tuple(sorted(p for p in params_paginados.items() if p[0] not in ('limit', 'offset')))
        data_params_tuple = tuple(sorted(params_paginados.items()))

        # 5a. Executar a query de contagem
        with st.spinner("Carregando total de registros..."):
            total_rows = get_filtered_row_count(count_query, count_params_tuple)
            st.session_state.total_rows = total_rows

        # 6a. Executar a query de dados
        with st.spinner(f"Carregando página {st.session_state.page}..."):
            df = load_paginated_data(query_paginada, data_params_tuple)

        # 7a. Renomear colunas
        if not df.empty:
            df = df.rename(columns=cc.COLUMN_MAPPING)

        if df.empty:
            st.warning("Nenhum dado encontrado com estes filtros e paginação.")
        else:
            # 8a. Seletor de Colunas
            all_available_columns = list(df.columns)
            DEFAULT_COLUMNS = ["Ano", "Média Geral"]
            default_safe = [col for col in DEFAULT_COLUMNS if col in all_available_columns]
            if not default_safe and all_available_columns:
                default_safe = all_available_columns[:5]

            st.markdown("#### 📊 Seleção de Colunas")
            selected_cols = st.multiselect(
                "Selecione as colunas para exibir:",
                options=all_available_columns,
                default=default_safe,
                key="column_selector"
            )
            
            # 9a. Exibir dataframe
            if selected_cols:
                st.dataframe(df[selected_cols], use_container_width=True, hide_index=True)
            else:
                st.info("Nenhuma coluna selecionada para exibição.")
            
            # 10a. Controles de Paginação 
            # (O seu código original de paginação e botões vai aqui)
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
                # Lógica do "CÓDIGO ANTIGO" (st.number_input)
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
                # Lógica do "CÓDIGO ANTIGO" (st.selectbox)
                page_size_options = [10, 25, 50, 100, "Todos"] # Simplificado da sua versão antiga
                
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
                is_last_page = (st.session_state.page >= total_pages)
                
                if st.button("Próximo ➡", disabled=(is_last_page or not show_pagination_controls), use_container_width=True):
                    change_page(1)
                    st.rerun()
            
            # 11a. Download PDF
            st.divider()
            if selected_cols:
                pdf_bytes = dataframe_to_pdf_bytes(df[selected_cols])
                st.download_button(
                    label="📥 Baixar esta página como PDF",
                    data=pdf_bytes,
                    file_name=f"{TABLE_NAME}_pagina_{st.session_state.page}_filtrada.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            else:
                st.warning("Selecione pelo menos uma coluna para gerar o PDF.")

    # ======================================================
    # ABA 2: GRÁFICOS
    # ======================================================
    with tab_graficos:
        st.header("Construtor de Gráficos")
        
        # 3b. Carregar listas de colunas
        try:
            col_lists = gu.get_column_lists()
            qual_cols = ["Nenhum"] + col_lists['qualitative']
            quant_cols = col_lists['quantitative']
            temp_cols = col_lists['temporal']
            id_cols = ["Nº de Inscrição"] + col_lists['id_for_count'] 
        except Exception as e:
            st.error(f"Erro ao carregar listas de colunas de graph_utils: {e}")
            st.stop()
        
        # --- Configuração do Gráfico (MOVIGO PARA CÁ) ---
        with st.expander("⚙️ 1. Configurar Gráfico", expanded=True):
            graph_type = st.selectbox(
                "Selecione o tipo de gráfico:",
                ["Dispersão (Correlação)", "Barras (Comparação)", "Linha (Temporal)", "Histograma (Distribuição)", "Boxplot (Distribuição)"],
                key="graph_type_selector" # Chave única
            )
        
        # --- Filtros Independentes (prefixo 'graph') ---
        # --- AJUSTE 2 AQUI ---
        # Captura o objeto expander e o passa como contêiner
        graph_filter_expander = st.expander("🔎 2. Filtros do Gráfico")
        render_filter_widgets(metadata, all_columns, container=graph_filter_expander, unique_prefix="graph")
        
        st.divider()

        # 4b. Construir a query para GRÁFICOS
        query_grafico, _, params_grafico_dict = build_query_and_params(
            metadata=metadata,
            reverse_mapping=reverse_mapping,
            enable_pagination=False, # Sem paginação
            unique_prefix="graph"  # Usa o prefixo 'graph'
        )
        query_tuple = (query_grafico,)
        params_tuple = tuple(sorted(params_grafico_dict.items()))
        
        # 5b. Lógica de Geração de Gráfico
        cols_to_load = []
        chart_generated = None

        if graph_type == "Dispersão (Correlação)":
            st.subheader("📈 Gráfico de Dispersão (Correlação)")
            st.markdown("Use para ver a relação entre **duas variáveis numéricas**.")
            col1, col2, col3 = st.columns(3)
            x_axis = col1.selectbox("Eixo X (Quantitativo):", quant_cols, index=quant_cols.index("Nota de Matemática"), key="g_scat_x")
            y_axis = col2.selectbox("Eixo Y (Quantitativo):", quant_cols, index=quant_cols.index("Nota da Redação"), key="g_scat_y")
            color = col3.selectbox("Cor (Categorias):", qual_cols, index=qual_cols.index("Região do Candidato"), key="g_scat_c")
            
            cols_to_load = [x_axis, y_axis]
            if color != "Nenhum": cols_to_load.append(color)

            if st.button("📊 Gerar Gráfico de Dispersão", use_container_width=True, key="btn_scat"):
                df_graph = load_graph_data(cols_to_load, query_tuple, params_tuple, reverse_mapping)
                if not df_graph.empty:
                    chart_generated = gu.create_scatter_plot(df_graph, x_axis, y_axis, color)

        elif graph_type == "Barras (Comparação)":
            st.subheader("📊 Gráfico de Barras (Comparação)")
            st.markdown("Use para **comparar uma métrica** (como média ou contagem) **entre categorias**.")
            col1, col2, col3, col4 = st.columns(4)
            x_axis_options = col_lists['qualitative'] + temp_cols
            x_axis = col1.selectbox("Eixo X (Categorias):", x_axis_options, index=x_axis_options.index("Região do Candidato"), key="g_bar_x")
            aggregation = col2.selectbox("Agregação:", ["Média", "Contagem", "Soma"], index=0, key="g_bar_agg")
            
            if aggregation == "Contagem":
                y_axis = col3.selectbox("Eixo Y (Contar):", id_cols, index=0, key="g_bar_y_count")
            else:
                y_axis = col3.selectbox("Eixo Y (Métrica):", quant_cols, index=quant_cols.index("Média Geral"), key="g_bar_y_metric")
            color = col4.selectbox("Agrupar por Cor:", qual_cols, index=0, key="g_bar_c")

            cols_to_load = [x_axis, y_axis]
            if color != "Nenhum": cols_to_load.append(color)

            if st.button("📊 Gerar Gráfico de Barras", use_container_width=True, key="btn_bar"):
                df_graph = load_graph_data(cols_to_load, query_tuple, params_tuple, reverse_mapping)
                if not df_graph.empty:
                    chart_generated = gu.create_bar_chart(df_graph, x_axis, y_axis, aggregation, color)

        elif graph_type == "Linha (Temporal)":
            st.subheader("📉 Gráfico de Linha (Temporal)")
            st.markdown("Use para ver a **evolução de uma métrica ao longo do tempo**.")
            col1, col2, col3, col4 = st.columns(4)
            x_axis = col1.selectbox("Eixo X (Tempo):", temp_cols, index=temp_cols.index("Ano"), key="g_line_x")
            aggregation = col2.selectbox("Agregação:", ["Média", "Contagem", "Soma"], index=0, key="g_line_agg")
            
            if aggregation == "Contagem":
                y_axis = col3.selectbox("Eixo Y (Contar):", id_cols, index=0, key="g_line_y_count")
            else:
                y_axis = col3.selectbox("Eixo Y (Métrica):", quant_cols, index=quant_cols.index("Média Geral"), key="g_line_y_metric")
            
            color_options = [c for c in qual_cols if c != "Ano"]
            color_index = color_options.index("Região do Candidato") if "Região do Candidato" in color_options else 0
            color = col4.selectbox("Dividir por (Linhas):", color_options, index=color_index, key="g_line_c")

            cols_to_load = [x_axis, y_axis]
            if color != "Nenhum": cols_to_load.append(color)
                
            if st.button("📊 Gerar Gráfico de Linha", use_container_width=True, key="btn_line"):
                df_graph = load_graph_data(cols_to_load, query_tuple, params_tuple, reverse_mapping)
                if not df_graph.empty:
                    chart_generated = gu.create_line_chart(df_graph, x_axis, y_axis, aggregation, color)

        elif graph_type == "Histograma (Distribuição)":
            st.subheader("Histograma (Distribuição)")
            st.markdown("Use para entender a **distribuição de uma única variável numérica**.")
            col1, col2 = st.columns(2)
            x_axis = col1.selectbox("Variável (Quantitativa):", quant_cols, index=quant_cols.index("Média Geral"), key="g_hist_x")
            color = col2.selectbox("Dividir por Cor:", qual_cols, index=0, key="g_hist_c")

            cols_to_load = [x_axis]
            if color != "Nenhum": cols_to_load.append(color)

            if st.button("📊 Gerar Histograma", use_container_width=True, key="btn_hist"):
                df_graph = load_graph_data(cols_to_load, query_tuple, params_tuple, reverse_mapping)
                if not df_graph.empty:
                    chart_generated = gu.create_histogram(df_graph, x_axis, color)

        elif graph_type == "Boxplot (Distribuição)":
            st.subheader("Boxplot (Distribuição por Categoria)")
            st.markdown("Use para **comparar a distribuição** de uma métrica **entre diferentes categorias**.")
            col1, col2 = st.columns(2)
            x_axis_options = [c for c in col_lists['qualitative'] if c != 'Renda Familiar'] + ['Renda Familiar']
            x_axis_index = x_axis_options.index("Renda Familiar") if "Renda Familiar" in x_axis_options else 0
            x_axis = col1.selectbox("Eixo X (Categorias):", x_axis_options, index=x_axis_index, key="g_box_x")
            y_axis = col2.selectbox("Eixo Y (Valores):", quant_cols, index=quant_cols.index("Média Geral"), key="g_box_y")

            cols_to_load = [x_axis, y_axis]

            if st.button("📊 Gerar Boxplot", use_container_width=True, key="btn_box"):
                df_graph = load_graph_data(cols_to_load, query_tuple, params_tuple, reverse_mapping)
                if not df_graph.empty:
                    chart_generated = gu.create_boxplot(df_graph, x_axis, y_axis)

        # 6b. Exibição do Gráfico
        if chart_generated:
            st.altair_chart(chart_generated, use_container_width=True)

except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.exception(e) 
    st.code(f"""
    Verifique:
    - Tabela '{TABLE_NAME}' existe?
    - Banco está rodando?
    - Credenciais corretas?
    - Mapeamento de colunas em 'column_config.py' está correto?
    """)