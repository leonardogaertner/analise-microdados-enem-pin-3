# pages/4_Questions_Performance.py

import sys
import os

import numpy as np
import pandas as pd
import pydeck as pdk
import streamlit as st

# Deixar o path certo para importar os services
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.db_config import DatabaseConfig
from services.database_manager import DatabaseManager
from services.performance_analyzer import PerformanceAnalyzer

# -------------------------------------
# Configuração básica da página
# -------------------------------------
st.set_page_config(layout="wide", page_title="Análise de Desempenho ENEM")

st.markdown(
    """
    <style>
        button[data-testid="stExpandSidebarButton"] { display: none !important; }
        div[data-testid="stToolbar"] {visibility: hidden !important;}

        .gabarito-container { 
            background-color: #1e1e1e; 
            padding: 20px; 
            border-radius: 10px;
            margin: 10px 0;
        }
        .numero-questao {
            font-size: 10px;
            color: #888;
            text-align: center;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🎯 Análise de Desempenho Pessoal - ENEM")

# -------------------------------------
# Inicializar serviços (DB + Analyzer)
# -------------------------------------
@st.cache_resource
def get_services():
    cfg = DatabaseConfig()
    db = DatabaseManager(cfg)
    analyzer = PerformanceAnalyzer(db)
    return db, analyzer

db_manager, analyzer = get_services()

if not db_manager.test_connection():
    st.error("❌ Erro de conexão com o banco de dados.")
    st.stop()

# -------------------------------------
# Configurações da Prova
# -------------------------------------
st.markdown("## ⚙️ Configurações da Prova")

col1, col2, col3, col4 = st.columns(4)

with col1:
    anos_disponiveis = list(range(2016, 2023))
    ano_prova = st.selectbox("Ano da Prova", anos_disponiveis, index=len(anos_disponiveis) - 1)

with col2:
    cor_prova = st.selectbox("Cor do Caderno", ["AZUL", "AMARELA", "ROSA", "CINZA", "BRANCA"])

with col3:
    lingua_label = st.selectbox("Língua Estrangeira", ["INGLÊS", "ESPANHOL"])
    lingua_backend = "INGLES" if lingua_label == "INGLÊS" else "ESPANHOL"

with col4:
    estados_br = [
        "Comparação Nacional", "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES",
        "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN",
        "RS", "RO", "RR", "SC", "SP", "SE", "TO"
    ]
    estado_sel = st.selectbox("Estado para Comparação", estados_br, index=0)
    estado_backend = None if estado_sel == "Comparação Nacional" else estado_sel

# Descobrir quantas questões a prova tem
qtd_questoes = analyzer.get_qtd_questoes(ano_prova, cor_prova, lingua_backend)
st.caption(
    f"Esta prova (ano {ano_prova}, cor {cor_prova}, {lingua_label}) possui **{qtd_questoes}** questões."
)

# -------------------------------------
# Session state para respostas e análise
# -------------------------------------
if "total_questoes" not in st.session_state:
    st.session_state.total_questoes = qtd_questoes

# Se mudar ano/cor/lingua, reinicializa se necessário
if st.session_state.total_questoes != qtd_questoes:
    st.session_state.total_questoes = qtd_questoes
    st.session_state.respostas = {i: "-" for i in range(1, qtd_questoes + 1)}
    st.session_state.input_sequencial = ""
    st.session_state.analise_resultado = None

if "respostas" not in st.session_state:
    st.session_state.respostas = {i: "-" for i in range(1, qtd_questoes + 1)}

if "input_sequencial" not in st.session_state:
    st.session_state.input_sequencial = ""

if "analise_resultado" not in st.session_state:
    st.session_state.analise_resultado = None

# -------------------------------------
# Preenchimento Sequencial
# -------------------------------------
st.markdown("## 📝 Preenchimento Rápido")

txt = st.text_area(
    "Digite suas respostas em sequência (A/B/C/D/E ou '-' para em branco).",
    value=st.session_state.input_sequencial,
    height=80,
)

col_a, col_b = st.columns(2)

with col_a:
    if st.button("🔄 Aplicar Sequência", type="primary", use_container_width=True):
        if not txt.strip():
            st.error("Digite alguma coisa primeiro.")
        else:
            # normaliza: pega apenas A/B/C/D/E/- e preenche/pad
            filtrados = [c for c in txt.upper() if c in "ABCDE-"]
            if len(filtrados) < qtd_questoes:
                filtrados += ["-"] * (qtd_questoes - len(filtrados))
            elif len(filtrados) > qtd_questoes:
                filtrados = filtrados[:qtd_questoes]

            st.session_state.input_sequencial = "".join(filtrados)
            for i in range(1, qtd_questoes + 1):
                st.session_state.respostas[i] = filtrados[i - 1]

            resp_validas = sum(1 for r in filtrados if r in "ABCDE")
            st.success(f"Sequência aplicada! {resp_validas} questões respondidas.")
            st.rerun()

with col_b:
    if st.button("🧹 Limpar", use_container_width=True):
        st.session_state.respostas = {i: "-" for i in range(1, qtd_questoes + 1)}
        st.session_state.input_sequencial = ""
        st.session_state.analise_resultado = None
        st.rerun()

total_respondidas = sum(1 for r in st.session_state.respostas.values() if r != "-")
percentual_respondidas = (total_respondidas / qtd_questoes) * 100 if qtd_questoes > 0 else 0
st.info(f"{total_respondidas}/{qtd_questoes} questões respondidas ({percentual_respondidas:.1f}%).")

if st.button("📈 GERAR ANÁLISE", type="primary", use_container_width=True):
    if total_respondidas == 0:
        st.error("Responda pelo menos uma questão para gerar a análise.")
    else:
        with st.spinner("Analisando..."):
            try:
                resultado = analyzer.analisar_desempenho(
                    respostas_dict=st.session_state.respostas,
                    ano=ano_prova,
                    cor_prova=cor_prova,
                    estado=estado_backend,
                    lingua=lingua_backend,
                )
                if "erro" in resultado:
                    st.error(resultado["erro"])
                else:
                    st.session_state.analise_resultado = resultado
                    st.success("Análise concluída.")
            except Exception as e:
                st.error(f"Erro na análise: {e}")

st.markdown("---")

# -------------------------------------
# Exibição dos resultados
# -------------------------------------
resultado = st.session_state.analise_resultado
if resultado is not None and "erro" not in resultado:
    st.markdown("## 📊 Resultados da Sua Análise")

    # Resumo geral
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Acertos Totais",
            f"{resultado['total_acertos']}/{resultado['total_questoes']}",
        )
    with col2:
        st.metric("Percentual de Acertos", f"{resultado['percentual_geral']}%")
    with col3:
        st.metric("Nota TRI Estimada", f"{resultado['nota_geral']:.1f}")
    with col4:
        base_comp = "Nacional" if resultado.get("estado") is None else resultado["estado"]
        st.metric("Base de Comparação", base_comp)

    if "info_prova" in resultado:
        st.info(
            f"📋 Prova identificada: {resultado['info_prova'].get('descricao', '')} "
            f"(match score: {resultado['info_prova'].get('match_score', 0)} acertos)"
        )

    # -----------------------------
    # Desempenho por área
    # -----------------------------
    st.markdown("### 📚 Desempenho por Área")

    res_areas = resultado["resultados_areas"]

    for area_code in ["CH", "CN", "LC", "MT"]:
        if area_code not in res_areas:
            continue

        dados_area = res_areas[area_code]
        nome_area = analyzer.areas_nomes.get(area_code, area_code)
        if area_code == "LC":
            nome_area += f" ({lingua_label})"

        titulo = (
            f"{nome_area} - {dados_area['acertos']}/{dados_area['total_questoes']} "
            f"({dados_area['percentual']:.1f}%) | Nota estimada: {dados_area['nota_estimada']:.1f}"
        )

        with st.expander(titulo, expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric(
                    "Acertos",
                    f"{dados_area['acertos']}/{dados_area['total_questoes']}",
                )
            with c2:
                st.metric("Percentual", f"{dados_area['percentual']:.1f}%")
            with c3:
                st.metric("Nota Estimada", f"{dados_area['nota_estimada']:.1f}")
            with c4:
                if dados_area.get("media_regional") is not None:
                    st.metric(
                        "Média do Estado",
                        f"{dados_area['media_regional']:.1f}",
                    )
                elif dados_area.get("media_nacional") is not None:
                    st.metric(
                        "Média Nacional",
                        f"{dados_area['media_nacional']:.1f}",
                    )
                else:
                    st.metric("Média", "—")

            st.progress(dados_area["percentual"] / 100)

    # -----------------------------
    # Melhor / pior área
    # -----------------------------
    st.markdown("### 🏆 Comparativo entre Áreas")

    melhor_area = max(res_areas.items(), key=lambda x: x[1]["nota_estimada"])
    pior_area = min(res_areas.items(), key=lambda x: x[1]["nota_estimada"])

    col_melhor, col_pior = st.columns(2)
    with col_melhor:
        nome = analyzer.areas_nomes.get(melhor_area[0], melhor_area[0])
        if melhor_area[0] == "LC":
            nome += f" ({lingua_label})"
        st.success(
            f"Melhor área: **{nome}**\n\n"
            f"- Nota: **{melhor_area[1]['nota_estimada']:.1f}**\n"
            f"- Acertos: **{melhor_area[1]['acertos']}/{melhor_area[1]['total_questoes']}**"
        )
    with col_pior:
        nome = analyzer.areas_nomes.get(pior_area[0], pior_area[0])
        if pior_area[0] == "LC":
            nome += f" ({lingua_label})"
        st.warning(
            f"Área a melhorar: **{nome}**\n\n"
            f"- Nota: **{pior_area[1]['nota_estimada']:.1f}**\n"
            f"- Acertos: **{pior_area[1]['acertos']}/{pior_area[1]['total_questoes']}**"
        )

    # -----------------------------
    # Tabela detalhada questão a questão
    # -----------------------------
    st.markdown("### 🔎 Detalhamento por Questão")

    detalhes = resultado.get("detalhes_questoes", [])
    if detalhes:
        df_det = pd.DataFrame(detalhes)
        df_det = df_det[
            ["numero", "area_nome", "resposta_oficial", "resposta_usuario", "status"]
        ]
        df_det.columns = [
            "Número da Questão",
            "Área",
            "Gabarito Oficial",
            "Gabarito Preenchido",
            "Acertou?",
        ]

        st.dataframe(df_det, use_container_width=True, hide_index=True)

        csv = df_det.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Baixar CSV com gabarito x respostas",
            data=csv,
            file_name=f"analise_enem_{ano_prova}_{cor_prova}.csv",
            mime="text/csv",
        )
    else:
        st.warning("Não foi possível montar o detalhamento questão a questão.")

    # -----------------------------
    # Comparação com médias (tabela)
    # -----------------------------
    st.markdown("### 🌎 Comparação com Médias e Mapa por Estado")

    medias = resultado.get("medias", {})
    medias_nac = medias.get("nacional", {})
    medias_estados = medias.get("por_estado", {})

    # Tabela resumo de comparação
    linhas_comp = []
    for area_code, dados_area in res_areas.items():
        linhas_comp.append(
            {
                "Área": analyzer.areas_nomes.get(area_code, area_code),
                "Nota Estimada (você)": dados_area["nota_estimada"],
                "Média Nacional": medias_nac.get(area_code),
                "Média do Estado (se selecionado)": (
                    medias_estados.get(estado_backend, {}).get(area_code)
                    if estado_backend
                    else None
                ),
            }
        )
    df_comp = pd.DataFrame(linhas_comp)
    st.dataframe(df_comp, use_container_width=True, hide_index=True)

    # -----------------------------
    # 🔹 Gráficos adicionais
    # -----------------------------
    st.markdown("### 📈 Gráficos adicionais de desempenho")

    # 1) Gráfico de barras: Nota estimada x médias por área
    if not df_comp.empty:
        st.subheader("Comparação de notas por área")

        df_notas = df_comp.set_index("Área")

        cols_notas = ["Nota Estimada (você)", "Média Nacional"]
        if "Média do Estado (se selecionado)" in df_notas.columns:
            cols_notas.append("Média do Estado (se selecionado)")

        st.bar_chart(df_notas[cols_notas])

    # 2) Gráfico de acertos x total de questões por área
    st.subheader("Acertos e total de questões por área")

    dados_barras = []
    for area_code, dados_area in res_areas.items():
        dados_barras.append(
            {
                "Área": analyzer.areas_nomes.get(area_code, area_code),
                "Acertos": dados_area["acertos"],
                "Total de Questões": dados_area["total_questoes"],
                "Percentual de Acertos": dados_area["percentual"],
            }
        )

    df_barras = pd.DataFrame(dados_barras).set_index("Área")
    st.bar_chart(df_barras[["Acertos", "Total de Questões"]])

    # -----------------------------
    # Mapa por UF (nota média em uma área escolhida)
    # -----------------------------
    if medias_estados:
        area_mapa_label = st.selectbox(
            "Área para visualizar no mapa:",
            ["CH", "CN", "LC", "MT"],
            format_func=lambda x: analyzer.areas_nomes.get(x, x),
        )

        UF_BOUNDING_BOX = {
            "AC": {"lat_min": -11.15, "lat_max": -7.12, "lon_min": -74.00, "lon_max": -66.60},
            "AL": {"lat_min": -10.48, "lat_max": -8.80, "lon_min": -38.20, "lon_max": -35.10},
            "AM": {"lat_min": -9.84,  "lat_max":  2.26, "lon_min": -73.80, "lon_max": -56.10},
            "AP": {"lat_min": -0.50,  "lat_max":  5.27, "lon_min": -54.70, "lon_max": -49.87},
            "BA": {"lat_min": -18.35, "lat_max": -8.00, "lon_min": -46.60, "lon_max": -37.30},
            "CE": {"lat_min": -7.85,  "lat_max": -2.72, "lon_min": -41.40, "lon_max": -37.00},
            "DF": {"lat_min": -16.06, "lat_max": -15.43, "lon_min": -48.30, "lon_max": -47.33},
            "ES": {"lat_min": -21.30, "lat_max": -17.89, "lon_min": -41.20, "lon_max": -39.40},
            "GO": {"lat_min": -19.75, "lat_max": -12.10, "lon_min": -53.26, "lon_max": -46.50},
            "MA": {"lat_min": -10.05, "lat_max": -1.05,  "lon_min": -46.65, "lon_max": -41.80},
            "MT": {"lat_min": -18.04, "lat_max": -7.00,  "lon_min": -61.80, "lon_max": -50.20},
            "MS": {"lat_min": -23.98, "lat_max": -17.14, "lon_min": -57.65, "lon_max": -50.80},
            "MG": {"lat_min": -22.91, "lat_max": -14.10, "lon_min": -51.00, "lon_max": -39.86},
            "PA": {"lat_min": -9.00,  "lat_max":  2.30, "lon_min": -56.10, "lon_max": -46.52},
            "PB": {"lat_min": -8.30,  "lat_max": -6.02, "lon_min": -38.80, "lon_max": -34.80},
            "PR": {"lat_min": -26.72, "lat_max": -22.50, "lon_min": -54.65, "lon_max": -48.00},
            "PE": {"lat_min": -9.48,  "lat_max": -7.30, "lon_min": -41.30, "lon_max": -34.80},
            "PI": {"lat_min": -10.95, "lat_max": -2.74, "lon_min": -45.98, "lon_max": -40.00},
            "RJ": {"lat_min": -23.40, "lat_max": -20.70, "lon_min": -44.80, "lon_max": -40.90},
            "RN": {"lat_min": -6.98,  "lat_max": -4.83, "lon_min": -38.60, "lon_max": -34.80},
            "RO": {"lat_min": -13.68, "lat_max": -7.97, "lon_min": -66.80, "lon_max": -59.80},
            "RR": {"lat_min":  0.00,  "lat_max":  5.27, "lon_min": -61.20, "lon_max": -59.33},
            "RS": {"lat_min": -33.75, "lat_max": -27.05, "lon_min": -57.65, "lon_max": -49.72},
            "SC": {"lat_min": -29.38, "lat_max": -25.99, "lon_min": -53.88, "lon_max": -48.33},
            "SE": {"lat_min": -11.50, "lat_max": -9.20, "lon_min": -38.40, "lon_max": -36.40},
            "SP": {"lat_min": -25.30, "lat_max": -19.80, "lon_min": -53.10, "lon_max": -44.10},
            "TO": {"lat_min": -13.50, "lat_max": -5.17, "lon_min": -50.70, "lon_max": -45.70},
        }

        linhas_mapa = []
        for uf, notas in medias_estados.items():
            bbox = UF_BOUNDING_BOX.get(uf)
            if not bbox:
                continue

            nota_area = notas.get(area_mapa_label)
            if nota_area is None:
                continue

            lat = (bbox["lat_min"] + bbox["lat_max"]) / 2
            lon = (bbox["lon_min"] + bbox["lon_max"]) / 2

            linhas_mapa.append(
                {
                    "uf": uf,
                    "nota": nota_area,
                    "lat": lat,
                    "lon": lon,
                }
            )

        if linhas_mapa:
            df_mapa = pd.DataFrame(linhas_mapa)
            df_mapa["raio"] = df_mapa["nota"] * 80

            layer = pdk.Layer(
                "ScatterplotLayer",
                data=df_mapa,
                get_position="[lon, lat]",
                get_radius="raio",
                get_fill_color=[255, 0, 0, 160],
                pickable=True,
            )

            view_state = pdk.ViewState(
                latitude=-14.2350,
                longitude=-51.9253,
                zoom=3,
                pitch=0,
            )

            st.pydeck_chart(
                pdk.Deck(
                    initial_view_state=view_state,
                    layers=[layer],
                    tooltip={"text": "{uf}: {nota}"},
                )
            )
        else:
            st.info("Não há dados suficientes para montar o mapa.")
