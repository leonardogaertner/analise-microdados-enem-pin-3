import streamlit as st
import sys
import os
import pandas as pd
import plotly.express as px
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.db_config import DatabaseConfig
from services.database_manager import DatabaseManager
from services.question_analyzer import QuestionAnalyzer

st.set_page_config(layout="wide", page_title="Análise de Questões ENEM")

st.markdown(
    """
    <style>
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 100%;
        }
        
        header {
            background: transparent;
        }
        
        button[data-testid="stExpandSidebarButton"] { 
            display: none !important; 
        }
        
        div[data-testid="stToolbar"] {
            visibility: hidden !important;
        }

        div.stButton > button {
            background: none;
            border: none;
            font-size: 22px;
            color: #FFFFFF;
            cursor: pointer;
            transition: 0.2s;
            margin-bottom: 1rem;
        }

        div.stButton > button:hover {
            color: #FF4B4B;
        }

        div[data-testid="stMetricValue"] {
            font-size: 28px;
            font-weight: bold;
        }
        
        .success-rate-info {
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #28a745;
            margin: 15px 0;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

if st.button("⬅", key="back_button"):
    st.switch_page("pages/4_Questions.py")

st.title("📊 Análise de Questões do ENEM")


@st.cache_resource
def get_services():
    config = DatabaseConfig()
    db_manager = DatabaseManager(config)
    analyzer = QuestionAnalyzer(db_manager)
    return db_manager, analyzer


db_manager, analyzer = get_services()


@st.cache_data(show_spinner=False)
def load_participants_data(
    ano: int,
    sigla_area: str | None = None,
    codigo_prova: int | None = None,
    limit: int = 5000,
) -> pd.DataFrame:
    base_query = """
        SELECT 
            "TX_RESPOSTAS_CH", "TX_RESPOSTAS_CN", "TX_RESPOSTAS_LC", "TX_RESPOSTAS_MT",
            "TX_GABARITO_CH", "TX_GABARITO_CN", "TX_GABARITO_LC", "TX_GABARITO_MT",
            "CO_PROVA_CH", "CO_PROVA_CN", "CO_PROVA_LC", "CO_PROVA_MT"
        FROM dados_enem_consolidado
        WHERE "NU_ANO" = :ano
    """

    params = {"ano": int(ano), "limit": int(limit)}

    area_to_col = {
        "CH": "CO_PROVA_CH",
        "CN": "CO_PROVA_CN",
        "LC": "CO_PROVA_LC",
        "MT": "CO_PROVA_MT",
    }

    if sigla_area and codigo_prova is not None:
        col_codigo = area_to_col.get(sigla_area)
        if col_codigo:
            base_query += f' AND "{col_codigo}" = :codigo_prova'
            params["codigo_prova"] = int(codigo_prova)

    base_query += " LIMIT :limit"

    try:
        return db_manager.execute_query(base_query, params)
    except Exception as e:
        st.error(f"Erro ao carregar dados dos participantes: {e}")
        return pd.DataFrame()


with st.spinner("Carregando questões do banco..."):
    df_questions = analyzer.load_questions()

if df_questions.empty:
    st.error("Não foi possível carregar os dados do banco de dados.")
    st.stop()

st.markdown("## 🎯 Selecione a Prova")

col1, col2 = st.columns(2)

with col1:
    anos_disponiveis = sorted(df_questions["ano"].dropna().unique(), reverse=True)
    ano_selecionado = st.selectbox(
        "📅 **Ano**",
        options=anos_disponiveis,
        index=0,
        help="Selecione o ano da prova do ENEM",
    )

df_filtrado = analyzer.filter_by_year(df_questions, ano_selecionado)

with col2:
    areas_disponiveis = sorted(df_filtrado["area"].dropna().unique())
    area_opcoes = ["Todas as áreas"] + list(areas_disponiveis)

    area_selecionada = st.selectbox(
        "📚 **Tipo (Área)**",
        options=area_opcoes,
        index=0,
        help="Área do conhecimento da prova. Selecione 'Todas as áreas' para ver tudo.",
    )

if area_selecionada != "Todas as áreas":
    df_filtrado = analyzer.filter_by_area(df_filtrado, area_selecionada)
    area_label = area_selecionada
else:
    area_label = "Todas as áreas"

sigla_area_atual = None
codigo_prova_atual = None

if area_selecionada != "Todas as áreas":
    if "sigla_area" in df_filtrado.columns and not df_filtrado["sigla_area"].isna().all():
        sigla_area_atual = str(df_filtrado["sigla_area"].dropna().iloc[0]).strip()

    if "provas" in df_filtrado.columns and not df_filtrado["provas"].isna().all():
        valor_provas = str(df_filtrado["provas"].dropna().iloc[0]).strip()
        try:
            codigo_prova_atual = int(valor_provas)
        except ValueError:
            nums = re.findall(r"\d+", valor_provas)
            if nums:
                try:
                    codigo_prova_atual = int(nums[0])
                except ValueError:
                    codigo_prova_atual = None

st.markdown("---")
with st.spinner("📊 Calculando taxas de acerto baseadas em participantes reais..."):
    df_participants = load_participants_data(
        ano=ano_selecionado,
        sigla_area=sigla_area_atual,
        codigo_prova=codigo_prova_atual,
    )
    df_filtrado_com_taxas = analyzer.calculate_real_success_rates(
        df_filtrado, df_participants
    )

participantes_count = len(df_participants) if not df_participants.empty else 0

st.info(
    f"📋 **Prova Selecionada:** {ano_selecionado} • {area_label} | "
    f"**{len(df_filtrado_com_taxas)} questões** | **{participantes_count} participantes analisados**"
)

if "taxa_acerto_real" in df_filtrado_com_taxas.columns and participantes_count > 0:
    taxa_media_real = df_filtrado_com_taxas["taxa_acerto_real"].mean()
    st.markdown(
        f"""
    <div class="success-rate-info">
        <strong>📈 Taxas de Acerto Reais:</strong> Baseadas em {participantes_count:,} participantes reais do ENEM {ano_selecionado}. 
        Média de acerto: <strong>{taxa_media_real:.1f}%</strong>
    </div>
    """,
        unsafe_allow_html=True,
    )
elif participantes_count == 0:
    st.warning(
        "⚠️ Não foram encontrados dados de participantes para esta prova. Usando taxas de acerto padrão."
    )

st.markdown("---")

with st.sidebar:
    st.header("🔍 Filtros Adicionais")
    st.markdown("---")

    st.subheader("📊 Taxa de Acerto")

    taxa_col = (
        "taxa_acerto_real"
        if "taxa_acerto_real" in df_filtrado_com_taxas.columns
        else "taxa_acerto_pct"
    )
    serie_taxa = df_filtrado_com_taxas[taxa_col]

    if (
        taxa_col == "taxa_acerto_real"
        and "participantes_amostra" in df_filtrado_com_taxas.columns
    ):
        serie_taxa = serie_taxa[df_filtrado_com_taxas["participantes_amostra"] > 0]

    if not serie_taxa.dropna().empty:
        taxa_min = float(serie_taxa.min())
        taxa_max = float(serie_taxa.max())
    else:
        taxa_min = 0.0
        taxa_max = 100.0

    taxa_selecionada = st.slider(
        "Filtrar por Taxa de Acerto (%)",
        min_value=0.0,
        max_value=100.0,
        value=(taxa_min, taxa_max),
        step=0.5,
        format="%.1f%%",
    )

    st.markdown("---")

    st.markdown("### 📋 Resumo")
    st.success(f"**{len(df_filtrado_com_taxas)}** questões encontradas")
    st.caption(f"Ano: **{ano_selecionado}**")
    st.caption(f"Tipo: **{area_label}**")
    if participantes_count > 0:
        st.caption(f"Participantes: **{participantes_count:,}**")

df_filtrado_final = analyzer.filter_by_success_rate(
    df_filtrado_com_taxas, taxa_selecionada[0], taxa_selecionada[1]
)

st.markdown("## 📊 Estatísticas da Prova")

stats = analyzer.get_statistics(df_filtrado_final)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total de Questões", stats["total_questoes"])

with col2:
    st.metric("Itens Abandonados", stats["itens_abandonados"])

with col3:
    st.metric(
        "Dificuldade Média",
        f"{stats['media_dificuldade']:.2f}"
        if stats["media_dificuldade"]
        else "N/A",
    )

with col4:
    taxa_acerto_text = (
        f"{stats['taxa_acerto_media']:.1f}%" if stats["taxa_acerto_media"] else "N/A"
    )
    if "taxa_acerto_real" in df_filtrado_final.columns and participantes_count > 0:
        taxa_acerto_text += " *"
    st.metric("Taxa de Acerto Média", taxa_acerto_text)

if "taxa_acerto_real" in df_filtrado_final.columns and participantes_count > 0:
    st.caption("* Baseada em dados reais de participantes")

st.markdown("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "📋 Tabela de Questões",
        "📈 Parâmetros TRI",
        "📊 Taxa de Acerto",
        "🎯 Análise de Gabaritos",
        "📈 Estatísticas",
    ]
)

with tab1:
    st.subheader("Tabela de Questões")

    colunas_display = [
        "numero_questao",
        "gabarito",
        "habilidade",
        "parametro_a",
        "parametro_b",
        "parametro_c",
        "item_abandonado",
        "motivo_abandono",
    ]

    if "taxa_acerto_real" in df_filtrado_final.columns:
        colunas_display.insert(2, "taxa_acerto_real")
        colunas_display.insert(3, "participantes_amostra")
    else:
        colunas_display.insert(2, "taxa_acerto_pct")

    df_display = df_filtrado_final[colunas_display].copy()

    df_display = df_display.rename(
        columns={
            "numero_questao": "Questão",
            "taxa_acerto_real": "Taxa Acerto Real (%)",
            "taxa_acerto_pct": "Taxa Acerto (%)",
            "participantes_amostra": "Amostra",
            "parametro_a": "Discriminação",
            "parametro_b": "Dificuldade",
            "parametro_c": "Acerto Casual",
        }
    )

    st.dataframe(df_display, use_container_width=True, hide_index=True, height=600)

with tab2:
    st.subheader("Análise dos Parâmetros da Teoria de Resposta ao Item (TRI)")

    col1, col2 = st.columns(2)

    with col1:
        fig_b = px.scatter(
            df_filtrado_final,
            x="numero_questao",
            y="parametro_b",
            title="Dificuldade das Questões (Parâmetro B)",
            labels={"numero_questao": "Número da Questão", "parametro_b": "Dificuldade"},
            color="parametro_b",
            color_continuous_scale="RdYlGn_r",
            hover_data=["gabarito", "habilidade"],
        )
        fig_b.update_layout(height=500)
        st.plotly_chart(fig_b, use_container_width=True)

    with col2:
        fig_a = px.scatter(
            df_filtrado_final,
            x="numero_questao",
            y="parametro_a",
            title="Discriminação das Questões (Parâmetro A)",
            labels={
                "numero_questao": "Número da Questão",
                "parametro_a": "Discriminação",
            },
            color="parametro_a",
            color_continuous_scale="Blues",
            hover_data=["gabarito", "habilidade"],
        )
        fig_a.update_layout(height=500)
        st.plotly_chart(fig_a, use_container_width=True)

    col3, col4 = st.columns(2)

    with col3:
        fig_hist_b = px.histogram(
            df_filtrado_final,
            x="parametro_b",
            nbins=20,
            title="Distribuição da Dificuldade",
            labels={"parametro_b": "Dificuldade", "count": "Quantidade"},
        )
        fig_hist_b.update_layout(height=400)
        st.plotly_chart(fig_hist_b, use_container_width=True)

    with col4:
        fig_hist_a = px.histogram(
            df_filtrado_final,
            x="parametro_a",
            nbins=20,
            title="Distribuição da Discriminação",
            labels={"parametro_a": "Discriminação", "count": "Quantidade"},
        )
        fig_hist_a.update_layout(height=400)
        st.plotly_chart(fig_hist_a, use_container_width=True)

    st.markdown("### 🔗 Correlação entre Parâmetros TRI")
    numeric_cols = [
        "parametro_a",
        "parametro_b",
        "parametro_c",
        "taxa_acerto_real"
        if "taxa_acerto_real" in df_filtrado_final.columns
        else "taxa_acerto_pct",
    ]
    numeric_cols = [col for col in numeric_cols if col in df_filtrado_final.columns]

    if len(numeric_cols) > 1:
        corr_matrix = df_filtrado_final[numeric_cols].corr()

        fig_corr = px.imshow(
            corr_matrix,
            title="Matriz de Correlação entre Parâmetros TRI e Taxa de Acerto",
            color_continuous_scale="RdBu_r",
            aspect="auto",
        )
        fig_corr.update_layout(height=500)
        st.plotly_chart(fig_corr, use_container_width=True)

with tab3:
    st.subheader("Análise de Taxa de Acerto")

    taxa_col_display = (
        "taxa_acerto_real"
        if "taxa_acerto_real" in df_filtrado_final.columns
        else "taxa_acerto_pct"
    )
    taxa_label = (
        "Taxa de Acerto Real (%)"
        if taxa_col_display == "taxa_acerto_real"
        else "Taxa de Acerto (%)"
    )

    col1, col2 = st.columns(2)

    with col1:
        fig_taxa = px.bar(
            df_filtrado_final,
            x="numero_questao",
            y=taxa_col_display,
            title=f"{taxa_label} por Questão",
            labels={"numero_questao": "Número da Questão", taxa_col_display: taxa_label},
            color=taxa_col_display,
            color_continuous_scale="RdYlGn",
            hover_data=["gabarito", "habilidade"],
        )
        fig_taxa.update_layout(height=500)
        st.plotly_chart(fig_taxa, use_container_width=True)

    with col2:
        fig_hist_taxa = px.histogram(
            df_filtrado_final,
            x=taxa_col_display,
            nbins=25,
            title=f"Distribuição da {taxa_label}",
            labels={
                taxa_col_display: taxa_label,
                "count": "Quantidade de Questões",
            },
            color_discrete_sequence=["#636EFA"],
        )
        fig_hist_taxa.update_layout(height=500)
        st.plotly_chart(fig_hist_taxa, use_container_width=True)

    st.markdown("### 🔍 Relação entre Dificuldade (Parâmetro B) e Taxa de Acerto")

    valid_trend = df_filtrado_final[["parametro_b", taxa_col_display]].dropna()
    use_trendline = (
        valid_trend.shape[0] >= 3 and valid_trend["parametro_b"].nunique() > 1
    )
    trendline_arg = "ols" if use_trendline else None

    fig_scatter = px.scatter(
        df_filtrado_final,
        x="parametro_b",
        y=taxa_col_display,
        title="Dificuldade (Parâmetro B) vs Taxa de Acerto",
        labels={
            "parametro_b": "Dificuldade (Parâmetro B)",
            taxa_col_display: taxa_label,
        },
        color=taxa_col_display,
        size="itens" if "itens" in df_filtrado_final.columns else None,
        color_continuous_scale="Viridis",
        hover_data=["numero_questao", "gabarito", "habilidade"],
        trendline=trendline_arg,
    )
    fig_scatter.update_layout(height=500)
    st.plotly_chart(fig_scatter, use_container_width=True)

    st.markdown("### 📊 Análise por Nível de Dificuldade")

    if "parametro_b" in df_filtrado_final.columns:
        df_filtrado_final["nivel_dificuldade"] = pd.cut(
            df_filtrado_final["parametro_b"],
            bins=[-10, -1, 0, 1, 10],
            labels=["Muito Fácil", "Fácil", "Médio", "Difícil"],
        )

        col3, col4 = st.columns(2)

        with col3:
            nivel_counts = (
                df_filtrado_final["nivel_dificuldade"].value_counts().sort_index()
            )
            fig_nivel = px.pie(
                values=nivel_counts.values,
                names=nivel_counts.index,
                title="Distribuição por Nível de Dificuldade",
                hole=0.4,
            )
            st.plotly_chart(fig_nivel, use_container_width=True)

        with col4:
            taxa_por_nivel = (
                df_filtrado_final.groupby("nivel_dificuldade", observed=False)[
                    taxa_col_display
                ]
                .mean()
                .reset_index()
            )
            fig_taxa_nivel = px.bar(
                taxa_por_nivel,
                x="nivel_dificuldade",
                y=taxa_col_display,
                title="Taxa Média de Acerto por Nível de Dificuldade",
                labels={
                    "nivel_dificuldade": "Nível de Dificuldade",
                    taxa_col_display: "Taxa de Acerto Média (%)",
                },
                color=taxa_col_display,
                color_continuous_scale="RdYlGn",
            )
            st.plotly_chart(fig_taxa_nivel, use_container_width=True)

    col5, col6 = st.columns(2)

    with col5:
        st.markdown("#### ✅ Top 10 Questões Mais Acertadas")
        top_acertadas = df_filtrado_final.nlargest(10, taxa_col_display)[
            ["numero_questao", "gabarito", taxa_col_display, "habilidade"]
        ]
        top_acertadas = top_acertadas.rename(
            columns={taxa_col_display: "Taxa Acerto (%)"}
        )
        st.dataframe(
            top_acertadas.style.background_gradient(
                subset=["Taxa Acerto (%)"], cmap="Greens"
            ),
            use_container_width=True,
            hide_index=True,
        )

    with col6:
        st.markdown("#### ❌ Top 10 Questões Menos Acertadas")
        top_erradas = df_filtrado_final.nsmallest(10, taxa_col_display)[
            ["numero_questao", "gabarito", taxa_col_display, "habilidade"]
        ]
        top_erradas = top_erradas.rename(
            columns={taxa_col_display: "Taxa Acerto (%)"}
        )
        st.dataframe(
            top_erradas.style.background_gradient(
                subset=["Taxa Acerto (%)"], cmap="Reds_r"
            ),
            use_container_width=True,
            hide_index=True,
        )

with tab4:
    st.subheader("Análise de Gabaritos")

    gabarito_counts = analyzer.get_answer_distribution(df_filtrado_final)

    col1, col2 = st.columns([1, 1])

    with col1:
        fig_gab = px.bar(
            gabarito_counts,
            x="Alternativa",
            y="Quantidade",
            title="Distribuição das Alternativas Corretas",
            labels={"Alternativa": "Alternativa", "Quantidade": "Quantidade de Questões"},
            color="Quantidade",
            color_continuous_scale="Viridis",
        )
        fig_gab.update_layout(height=400)
        st.plotly_chart(fig_gab, use_container_width=True)

    with col2:
        fig_pie = px.pie(
            gabarito_counts,
            values="Quantidade",
            names="Alternativa",
            title="Proporção de Gabaritos",
            hole=0.4,
        )
        fig_pie.update_layout(height=400)
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("### 🧩 Análise de Padrões de Gabarito")

    if len(df_filtrado_final) >= 10:
        df_sorted = df_filtrado_final.sort_values("numero_questao")
        sequencias = df_sorted["gabarito"].values

        fig_sequencia = px.line(
            x=range(1, len(sequencias) + 1),
            y=[ord(gab) - 64 for gab in sequencias],
            title="Sequência de Gabaritos ao Longo da Prova",
            labels={
                "x": "Número da Questão",
                "y": "Gabarito (A=1, B=2, C=3, D=4, E=5)",
            },
            markers=True,
        )
        fig_sequencia.update_layout(height=400)
        st.plotly_chart(fig_sequencia, use_container_width=True)

    st.markdown("### 📊 Resumo Estatístico dos Gabaritos")

    total_questoes = len(df_filtrado_final)
    gabarito_stats = gabarito_counts.copy()
    gabarito_stats["Percentual"] = (
        gabarito_stats["Quantidade"] / total_questoes * 100
    ).round(1)

    st.dataframe(
        gabarito_stats.style.background_gradient(
            subset=["Quantidade", "Percentual"], cmap="YlOrRd"
        ),
        use_container_width=True,
        hide_index=True,
    )

with tab5:
    st.subheader("Estatísticas Detalhadas")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 📊 Parâmetros TRI")
        stats_tri = analyzer.get_tri_statistics(df_filtrado_final)
        st.dataframe(
            stats_tri.style.format(
                {"Média": "{:.3f}", "Mediana": "{:.3f}", "Desvio Padrão": "{:.3f}"}
            ),
            use_container_width=True,
            hide_index=True,
        )

    with col2:
        st.markdown("#### 🎯 Habilidades Mais Cobradas")
        habilidades = analyzer.get_top_skills(df_filtrado_final, n=10)
        st.dataframe(
            habilidades,
            use_container_width=True,
            hide_index=True,
            height=350,
        )

    if stats["itens_abandonados"] > 0:
        st.markdown("#### ⚠️ Questões Abandonadas")
        df_abandonadas = analyzer.get_abandoned_questions(df_filtrado_final)
        st.dataframe(
            df_abandonadas,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("✅ Nenhuma questão foi abandonada nesta prova!")

    if area_selecionada == "Todas as áreas":
        st.markdown("#### 📚 Estatísticas por Área do Conhecimento")

        col_taxa_area = (
            "taxa_acerto_real"
            if "taxa_acerto_real" in df_filtrado_final.columns
            else "taxa_acerto_pct"
        )

        stats_por_area = (
            df_filtrado_final.groupby("area")
            .agg(
                {
                    "numero_questao": "count",
                    "parametro_b": "mean",
                    col_taxa_area: "mean",
                    "item_abandonado": "sum",
                }
            )
            .reset_index()
        )

        stats_por_area = stats_por_area.rename(
            columns={
                "numero_questao": "Total Questões",
                "parametro_b": "Dificuldade Média",
                col_taxa_area: "Taxa Acerto Média (%)",
                "item_abandonado": "Questões Abandonadas",
            }
        )

        stats_por_area["Dificuldade Média"] = stats_por_area[
            "Dificuldade Média"
        ].round(3)
        stats_por_area["Taxa Acerto Média (%)"] = stats_por_area[
            "Taxa Acerto Média (%)"
        ].round(1)

        st.dataframe(
            stats_por_area.style.background_gradient(
                subset=["Dificuldade Média", "Taxa Acerto Média (%)"],
                cmap="RdYlGn_r",
            ),
            use_container_width=True,
            hide_index=True,
        )

    if len(df_questions["ano"].unique()) > 1 and area_selecionada != "Todas as áreas":
        st.markdown("#### 📅 Evolução Temporal da Dificuldade")

        evolucao_dificuldade = (
            df_questions[df_questions["area"] == area_selecionada]
            .groupby("ano")
            .agg({"parametro_b": "mean"})
            .reset_index()
        )

        fig_evolucao = px.line(
            evolucao_dificuldade,
            x="ano",
            y="parametro_b",
            title=f"Evolução da Dificuldade Média em {area_selecionada}",
            labels={"ano": "Ano", "parametro_b": "Dificuldade Média (Parâmetro B)"},
            markers=True,
        )
        st.plotly_chart(fig_evolucao, use_container_width=True)

st.markdown("---")
if "taxa_acerto_real" in df_filtrado_final.columns and participantes_count > 0:
    st.caption(
        "💡 **Dica:** As taxas de acerto são calculadas com base em participantes reais do ENEM (para um código de prova específico quando possível). Os parâmetros A, B e C são da Teoria de Resposta ao Item (TRI). O Parâmetro B indica a dificuldade (quanto maior, mais difícil), o Parâmetro A indica a discriminação (capacidade de diferenciar candidatos), e o Parâmetro C indica a probabilidade de acerto casual."
    )
else:
    st.caption(
        "💡 **Dica:** Os parâmetros A, B e C são da Teoria de Resposta ao Item (TRI). O Parâmetro B indica a dificuldade (quanto maior, mais difícil), o Parâmetro A indica a discriminação (capacidade de diferenciar candidatos), e o Parâmetro C indica a probabilidade de acerto casual."
    )
