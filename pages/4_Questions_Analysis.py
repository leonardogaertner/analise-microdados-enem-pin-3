import streamlit as st
import sys
import os
import pandas as pd
import plotly.express as px

# Adicionar diretórios ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.db_config import DatabaseConfig
from services.database_manager import DatabaseManager
from services.question_analyzer import QuestionAnalyzer

# Estilos CSS
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

        div[data-testid="stMetricValue"] {
            font-size: 28px;
            font-weight: bold;
        }
    </style>
""", unsafe_allow_html=True)

if st.button("⬅", key="back_button"):
    st.switch_page("pages/4_Questions.py")

st.title("📊 Análise de Questões do ENEM")

# Inicializar serviços com cache
@st.cache_resource
def get_services():
    """Inicializa e retorna os serviços necessários."""
    config = DatabaseConfig()
    db_manager = DatabaseManager(config)
    analyzer = QuestionAnalyzer(db_manager)
    return db_manager, analyzer

db_manager, analyzer = get_services()

# Carregar dados
with st.spinner("Carregando dados do banco..."):
    df = analyzer.load_questions()

if df.empty:
    st.error("Não foi possível carregar os dados do banco de dados.")
    st.stop()

# --- Seção de Seleção de Prova ---
st.markdown("## 🎯 Selecione a Prova")

col1, col2, col3 = st.columns(3)

with col1:
    anos_disponiveis = sorted(df['ano'].dropna().unique(), reverse=True)
    ano_selecionado = st.selectbox(
        "📅 **Ano**",
        options=anos_disponiveis,
        index=0,
        help="Selecione o ano da prova do ENEM"
    )

# Filtrar por ano
df_filtrado = analyzer.filter_by_year(df, ano_selecionado)

with col2:
    cores_disponiveis = sorted(df_filtrado['cor'].dropna().unique())
    cor_selecionada = st.selectbox(
        "🎨 **Cor da Prova**",
        options=cores_disponiveis,
        help="Cada cor representa uma versão diferente da prova"
    )

# Filtrar por cor
df_filtrado = analyzer.filter_by_color(df_filtrado, cor_selecionada)

with col3:
    areas_disponiveis = sorted(df_filtrado['area'].dropna().unique())
    area_selecionada = st.selectbox(
        "📚 **Tipo (Área)**",
        options=areas_disponiveis,
        help="Área do conhecimento da prova"
    )

# Filtrar por área
df_filtrado = analyzer.filter_by_area(df_filtrado, area_selecionada)

# Informação da prova selecionada
st.info(f"📋 **Prova Selecionada:** {ano_selecionado} • {cor_selecionada} • {area_selecionada} | **{len(df_filtrado)} questões**")

st.markdown("---")

# --- Sidebar: Filtros Adicionais ---
st.sidebar.header("🔍 Filtros Adicionais")
st.sidebar.markdown("---")

# Filtro por Taxa de Acerto (Slider)
st.sidebar.subheader("📊 Taxa de Acerto")

# Obter valores mínimo e máximo da taxa de acerto
taxa_min = float(df_filtrado['taxa_acerto_pct'].min())
taxa_max = float(df_filtrado['taxa_acerto_pct'].max())

# Slider de intervalo
taxa_selecionada = st.sidebar.slider(
    "Filtrar por Taxa de Acerto (%)",
    min_value=0.0,
    max_value=100.0,
    value=(taxa_min, taxa_max),
    step=0.5,
    format="%.1f%%"
)

# Aplicar filtro de taxa de acerto
df_filtrado = analyzer.filter_by_success_rate(df_filtrado, taxa_selecionada[0], taxa_selecionada[1])

st.sidebar.markdown("---")

# Resumo dos filtros aplicados
st.sidebar.markdown("### 📋 Resumo")
st.sidebar.success(f"**{len(df_filtrado)}** questões encontradas")
st.sidebar.caption(f"Ano: **{ano_selecionado}**")
st.sidebar.caption(f"Cor: **{cor_selecionada}**")
st.sidebar.caption(f"Tipo: **{area_selecionada}**")

# --- Métricas Principais ---
st.markdown("## 📊 Estatísticas da Prova")

stats = analyzer.get_statistics(df_filtrado)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total de Questões", stats['total_questoes'])

with col2:
    st.metric("Itens Abandonados", stats['itens_abandonados'])

with col3:
    st.metric("Dificuldade Média", f"{stats['media_dificuldade']:.2f}" if stats['media_dificuldade'] else "N/A")

with col4:
    st.metric("Taxa de Acerto Média", f"{stats['taxa_acerto_media']:.1f}%" if stats['taxa_acerto_media'] else "N/A")

st.markdown("---")

# --- Tabs para diferentes visualizações ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Tabela de Questões", "📈 Parâmetros TRI", "📊 Taxa de Acerto", "🎯 Análise de Gabaritos", "📈 Estatísticas"])

with tab1:
    st.subheader("Tabela de Questões")

    # Preparar tabela para exibição
    df_display = df_filtrado[[
        'numero_questao', 'gabarito', 'taxa_acerto_pct', 'habilidade',
        'parametro_a', 'parametro_b', 'parametro_c',
        'item_abandonado', 'motivo_abandono'
    ]].copy()

    df_display = df_display.rename(columns={
        'numero_questao': 'Questão',
        'parametro_a': 'Discriminação',
        'parametro_b': 'Dificuldade',
        'parametro_c': 'Acerto Casual'
    })

    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        height=500
    )

with tab2:
    st.subheader("Análise dos Parâmetros da Teoria de Resposta ao Item (TRI)")

    col1, col2 = st.columns(2)

    with col1:
        # Gráfico de Dificuldade (Parâmetro B)
        fig_b = px.scatter(
            df_filtrado,
            x='numero_questao',
            y='parametro_b',
            title='Dificuldade das Questões (Parâmetro B)',
            labels={'numero_questao': 'Número da Questão', 'parametro_b': 'Dificuldade'},
            color='parametro_b',
            color_continuous_scale='RdYlGn_r',
            hover_data=['gabarito', 'habilidade']
        )
        fig_b.update_layout(height=400)
        st.plotly_chart(fig_b, use_container_width=True)

    with col2:
        # Gráfico de Discriminação (Parâmetro A)
        fig_a = px.scatter(
            df_filtrado,
            x='numero_questao',
            y='parametro_a',
            title='Discriminação das Questões (Parâmetro A)',
            labels={'numero_questao': 'Número da Questão', 'parametro_a': 'Discriminação'},
            color='parametro_a',
            color_continuous_scale='Blues',
            hover_data=['gabarito', 'habilidade']
        )
        fig_a.update_layout(height=400)
        st.plotly_chart(fig_a, use_container_width=True)

    # Histograma dos Parâmetros
    col3, col4 = st.columns(2)

    with col3:
        fig_hist_b = px.histogram(
            df_filtrado,
            x='parametro_b',
            nbins=20,
            title='Distribuição da Dificuldade',
            labels={'parametro_b': 'Dificuldade', 'count': 'Quantidade'}
        )
        st.plotly_chart(fig_hist_b, use_container_width=True)

    with col4:
        fig_hist_a = px.histogram(
            df_filtrado,
            x='parametro_a',
            nbins=20,
            title='Distribuição da Discriminação',
            labels={'parametro_a': 'Discriminação', 'count': 'Quantidade'}
        )
        st.plotly_chart(fig_hist_a, use_container_width=True)

with tab3:
    st.subheader("Análise de Taxa de Acerto")

    col1, col2 = st.columns(2)

    with col1:
        # Gráfico de Taxa de Acerto por Questão
        fig_taxa = px.bar(
            df_filtrado,
            x='numero_questao',
            y='taxa_acerto_pct',
            title='Taxa de Acerto por Questão',
            labels={'numero_questao': 'Número da Questão', 'taxa_acerto_pct': 'taxa_acerto_pct'},
            color='taxa_acerto_pct',
            color_continuous_scale='RdYlGn',
            hover_data=['gabarito', 'habilidade']
        )
        fig_taxa.update_layout(height=400)
        st.plotly_chart(fig_taxa, use_container_width=True)

    with col2:
        # Distribuição da Taxa de Acerto
        fig_hist_taxa = px.histogram(
            df_filtrado,
            x='taxa_acerto_pct',
            nbins=25,
            title='Distribuição da Taxa de Acerto',
            labels={'taxa_acerto_pct': 'taxa_acerto_pct', 'count': 'Quantidade de Questões'},
            color_discrete_sequence=['#636EFA']
        )
        fig_hist_taxa.update_layout(height=400)
        st.plotly_chart(fig_hist_taxa, use_container_width=True)

    # Relação entre Dificuldade e Taxa de Acerto
    st.markdown("### 🔍 Relação entre Dificuldade (TRI) e Taxa de Acerto")

    fig_scatter = px.scatter(
        df_filtrado,
        x='parametro_b',
        y='taxa_acerto_pct',
        title='Dificuldade (Parâmetro B) vs Taxa de Acerto',
        labels={'parametro_b': 'Dificuldade (Parâmetro B)', 'taxa_acerto_pct': 'taxa_acerto_pct'},
        color='taxa_acerto_pct',
        size='itens',
        color_continuous_scale='Viridis',
        hover_data=['numero_questao', 'gabarito', 'habilidade'],
        trendline='ols'
    )
    fig_scatter.update_layout(height=500)
    st.plotly_chart(fig_scatter, use_container_width=True)

    # Top questões mais e menos acertadas
    col3, col4 = st.columns(2)

    with col3:
        st.markdown("#### ✅ Top 10 Questões Mais Acertadas")
        top_acertadas = df_filtrado.nlargest(10, 'taxa_acerto_pct')[['numero_questao', 'gabarito', 'taxa_acerto_pct', 'habilidade']]
        st.dataframe(
            top_acertadas.style.background_gradient(subset=['taxa_acerto_pct'], cmap='Greens'),
            use_container_width=True,
            hide_index=True
        )

    with col4:
        st.markdown("#### ❌ Top 10 Questões Menos Acertadas")
        top_erradas = df_filtrado.nsmallest(10, 'taxa_acerto_pct')[['numero_questao', 'gabarito', 'taxa_acerto_pct', 'habilidade']]
        st.dataframe(
            top_erradas.style.background_gradient(subset=['taxa_acerto_pct'], cmap='Reds_r'),
            use_container_width=True,
            hide_index=True
        )

with tab4:
    st.subheader("Análise de Gabaritos")

    # Distribuição de Gabaritos
    gabarito_counts = analyzer.get_answer_distribution(df_filtrado)

    col1, col2 = st.columns([1, 1])

    with col1:
        fig_gab = px.bar(
            gabarito_counts,
            x='Alternativa',
            y='Quantidade',
            title='Distribuição das Alternativas Corretas',
            labels={'Alternativa': 'Alternativa', 'Quantidade': 'Quantidade de Questões'},
            color='Quantidade',
            color_continuous_scale='Viridis'
        )
        st.plotly_chart(fig_gab, use_container_width=True)

    with col2:
        fig_pie = px.pie(
            gabarito_counts,
            values='Quantidade',
            names='Alternativa',
            title='Proporção de Gabaritos',
            hole=0.4
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # Tabela de resumo
    st.markdown("### 📊 Resumo Estatístico dos Gabaritos")
    st.dataframe(
        gabarito_counts.style.background_gradient(subset=['Quantidade'], cmap='YlOrRd'),
        use_container_width=True,
        hide_index=True
    )

with tab5:
    st.subheader("Estatísticas Detalhadas")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📊 Parâmetros TRI")
        stats_tri = analyzer.get_tri_statistics(df_filtrado)
        st.dataframe(
            stats_tri.style.format({'Média': '{:.3f}', 'Mediana': '{:.3f}', 'Desvio Padrão': '{:.3f}'}),
            use_container_width=True,
            hide_index=True
        )

    with col2:
        st.markdown("#### 🎯 Habilidades Mais Cobradas")
        habilidades = analyzer.get_top_skills(df_filtrado, n=10)
        st.dataframe(
            habilidades,
            use_container_width=True,
            hide_index=True,
            height=250
        )

    # Questões Abandonadas
    if stats['itens_abandonados'] > 0:
        st.markdown("#### ⚠️ Questões Abandonadas")
        df_abandonadas = analyzer.get_abandoned_questions(df_filtrado)
        st.dataframe(
            df_abandonadas,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("✅ Nenhuma questão foi abandonada nesta prova!")

# --- Footer ---
st.markdown("---")
st.caption("💡 **Dica:** Os parâmetros A, B e C são da Teoria de Resposta ao Item (TRI). O Parâmetro B indica a dificuldade (quanto maior, mais difícil), o Parâmetro A indica a discriminação (capacidade de diferenciar candidatos), e o Parâmetro C indica a probabilidade de acerto casual.")
