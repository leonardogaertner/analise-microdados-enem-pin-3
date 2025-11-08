# pages/4_Questions.py
import streamlit as st
import pandas as pd
import altair as alt

# Importações corrigidas
try:
    from Exploration.db_utils import get_engine, TABLE_NAME
    from Exploration import graph_utils as gu
    from Exploration import column_config as cc
except ImportError:
    st.error("Erro ao carregar módulos. Verifique a estrutura de pastas 'Exploration'.")
    st.stop()


# Configuração da Página
st.set_page_config(layout="wide")
st.title("🔍 Insights Pré-Definidos")

engine = get_engine()
if engine is None:
    st.stop()

# Função auxiliar para carregar dados específicos
@st.cache_data(ttl=3600)
def load_specific_data(columns: list, filters: dict = None):
    reverse_mapping = {v: k.upper() for k, v in cc.COLUMN_MAPPING.items()}
    db_cols = []
    for col in columns:
        db_col = reverse_mapping.get(col)
        if db_col:
            db_cols.append(f'"{db_col}"')
        else:
            st.warning(f"Coluna de insight '{col}' não encontrada no mapeamento.")
            
    if not db_cols:
        return pd.DataFrame()

    query = f'SELECT {", ".join(db_cols)} FROM "{TABLE_NAME}"'
    params = {}
    
    if filters:
        where_clauses = []
        param_idx = 0
        for col, value in filters.items():
            db_col = reverse_mapping.get(col)
            if db_col is None: 
                st.warning(f"Coluna de filtro '{col}' não encontrada.")
                continue
            
            # Cria nomes de parâmetros únicos (ex: p0, p1)
            param_name = f'p{param_idx}'
            param_idx += 1
            
            if isinstance(value, list) or isinstance(value, tuple):
                # Cláusula IN precisa de uma tupla
                where_clauses.append(f'"{db_col}" IN %({param_name})s')
                params[param_name] = tuple(value)
            else:
                # Cláusula =
                where_clauses.append(f'"{db_col}" = %({param_name})s')
                params[param_name] = value
                
        if where_clauses:
            query += ' WHERE ' + ' AND '.join(where_clauses)
    
    try:
        df = pd.read_sql_query(query, engine, params=params)
        df.columns = df.columns.str.upper()
        df = df.rename(columns=cc.COLUMN_MAPPING)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados para insight: {e}")
        st.code(query)
        st.code(params)
        return pd.DataFrame()


# --- Perguntas ---

# Pergunta 1
st.header("1. Como a média da nota de redação evoluiu ao longo dos anos por região?")
with st.spinner("Carregando Pergunta 1..."):
    cols_p1 = ["Ano", "Nota da Redação", "Região do Candidato"]
    df1 = load_specific_data(cols_p1)
    if not df1.empty:
        chart1 = gu.create_line_chart(df1, "Ano", "Nota da Redação", "Média", "Região do Candidato")
        st.altair_chart(chart1, use_container_width=True)
        st.markdown("**Insight:** Observa-se uma tendência de variação na média das notas de redação ao longo dos anos, com diferenças claras entre as regiões.")
    else:
        st.warning("Sem dados para Pergunta 1.")

# Pergunta 2
st.header("2. Qual é a relação entre a escolaridade dos pais e a média geral dos alunos?")
with st.spinner("Carregando Pergunta 2..."):
    cols_p2 = ["Escolaridade dos Pais", "Média Geral"]
    df2 = load_specific_data(cols_p2)
    if not df2.empty:
        chart2 = gu.create_boxplot(df2, "Escolaridade dos Pais", "Média Geral")
        st.altair_chart(chart2, use_container_width=True)
        st.markdown("**Insight:** Alunos com pais de maior escolaridade (ex: pós-graduação) tendem a ter médias gerais mais altas e com menos variação (distribuição mais 'compacta').")
    else:
        st.warning("Sem dados para Pergunta 2.")

# Pergunta 3
st.header("3. Qual a distribuição das notas de matemática (Pública vs. Privada)?")
with st.spinner("Carregando Pergunta 3..."):
    cols_p3 = ["Nota de Matemática", "Tipo da Escola"]
    # Garante que os valores do filtro batam com os dados
    filters_p3 = {"Tipo da Escola": ["Pública", "Privada"]} 
    df3 = load_specific_data(cols_p3, filters_p3)
    if not df3.empty:
        chart3 = gu.create_histogram(df3, "Nota de Matemática", "Tipo da Escola")
        st.altair_chart(chart3, use_container_width=True)
        st.markdown("**Insight:** A distribuição das notas de matemática em escolas privadas é visivelmente deslocada para valores mais altos em comparação com escolas públicas.")
    else:
        st.warning("Sem dados para Pergunta 3 (Verifique se os valores 'Pública' e 'Privada' existem).")

# Pergunta 4
st.header("4. Como a renda familiar afeta a nota em ciências da natureza?")
with st.spinner("Carregando Pergunta 4..."):
    cols_p4 = ["Renda Familiar", "Nota de Ciências da Natureza"]
    df4 = load_specific_data(cols_p4)
    if not df4.empty:
        chart4 = gu.create_bar_chart(df4, "Renda Familiar", "Nota de Ciências da Natureza", "Média")
        st.altair_chart(chart4, use_container_width=True)
        st.markdown("**Insight:** Há uma correlação positiva clara: faixas de renda mais altas estão associadas a médias maiores em ciências da natureza.")
    else:
        st.warning("Sem dados para Pergunta 4.")

# Pergunta 5
st.header("5. Evolução do número de treineiros ao longo dos anos")
with st.spinner("Carregando Pergunta 5..."):
    cols_p5 = ["Ano", "Treineiro?"]
    # Garante que os valores do filtro batam com os dados (ex: 'Sim' ou '1')
    filters_p5 = {"Treineiro?": "Sim"} # Ajuste 'Sim' se o valor for '1' ou outro
    df5 = load_specific_data(cols_p5, filters_p5)
    if not df5.empty:
        # Usamos 'Nº de Inscrição' (ou qualquer ID) para contagem
        df5_count = load_specific_data(["Ano", "Nº de Inscrição"], filters_p5)
        chart5 = gu.create_line_chart(df5_count, "Ano", "Nº de Inscrição", "Contagem")
        st.altair_chart(chart5, use_container_width=True)
        st.markdown("**Insight:** O número de 'Treineiros' (filtrados) mostra uma tendência de crescimento ao longo dos anos.")
    else:
        st.warning("Sem dados para Pergunta 5 (Verifique o valor do filtro 'Treineiro?').")