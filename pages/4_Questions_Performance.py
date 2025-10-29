import streamlit as st
import sys
import os

# Adicionar diretórios ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.db_config import DatabaseConfig
from services.database_manager import DatabaseManager
from services.performance_analyzer import PerformanceAnalyzer

# Configuração da página
st.set_page_config(layout="wide")

# Estilos CSS
st.markdown("""
    <style>
        button[data-testid="stExpandSidebarButton"] { display: none !important; }
        div[data-testid="stToolbar"] {visibility: hidden !important;}
        .gabarito-container { background-color: #2d2d2d; padding: 20px; border-radius: 10px; max-height: 520px; overflow-y: auto; }
        .gabarito-container h3 { color: #fff; position: sticky; top: 0; background:#2d2d2d; padding-top:10px; }
        .stRadio > div { flex-direction: row !important; gap: 6px !important; }
        div[role="radiogroup"] label[data-checked="true"] { background-color: #ff4b4b !important; }

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

if st.button("⬅", key="back_button"):
    st.switch_page("pages/4_Questions.py")

st.title("🎯 Análise de Desempenho Pessoal")

# Inicializar serviços com cache
@st.cache_resource
def get_services():
    """Inicializa e retorna os serviços necessários."""
    config = DatabaseConfig()
    db_manager = DatabaseManager(config)
    analyzer = PerformanceAnalyzer(db_manager)
    return db_manager, analyzer

db_manager, analyzer = get_services()

# Testar conexão
if not db_manager.test_connection():
    st.stop()

# Inicializar session state
if "respostas" not in st.session_state:
    st.session_state.respostas = {i: "-" for i in range(1, 181)}

if "analise_resultado" not in st.session_state:
    st.session_state.analise_resultado = None

# --- Formulário de Gabarito ---
st.markdown("## Preencha seu gabarito")
st.markdown('<div class="gabarito-container">', unsafe_allow_html=True)
st.markdown('<h3>Folha de Respostas</h3>', unsafe_allow_html=True)

questoes_por_linha = 5
total_questoes = 180
opt_list = ["-", "A", "B", "C", "D", "E"]

for linha_inicio in range(0, total_questoes, questoes_por_linha):
    cols = st.columns(questoes_por_linha)
    for col_idx in range(questoes_por_linha):
        q_num = linha_inicio + col_idx + 1
        if q_num <= total_questoes:
            with cols[col_idx]:
                resposta_atual = st.session_state.respostas.get(q_num, "-")
                try:
                    index_selecionado = opt_list.index(resposta_atual)
                except ValueError:
                    index_selecionado = 0
                resposta = st.selectbox(
                    f"{q_num:03d}",
                    options=opt_list,
                    index=index_selecionado,
                    key=f"q_{q_num}",
                    label_visibility="visible"
                )
                st.session_state.respostas[q_num] = resposta

st.markdown('</div>', unsafe_allow_html=True)

total_respondidas = sum(1 for r in st.session_state.respostas.values() if r is not None and r != "-")
percentual = (total_respondidas / 180) * 100

st.markdown("---")
st.markdown("### Configurações da Análise")
col_config1, col_config2, col_config3 = st.columns(3)

with col_config1:
    anos_disponiveis = list(range(2014, 2024))
    ano_prova = st.selectbox("Ano da Prova", anos_disponiveis, index=len(anos_disponiveis)-1)

with col_config2:
    cor_prova = st.selectbox("Cor do Caderno (apenas referência)", ["AZUL", "AMARELA", "ROSA", "CINZA"], index=0)

with col_config3:
    estados_br = ["Selecione...", "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"]
    estado = st.selectbox("Estado (opcional)", estados_br, index=0)
    if estado == "Selecione...":
        estado = None

col1, col2 = st.columns([3,1])

with col1:
    if st.button("Gerar Análise de Desempenho", use_container_width=True, type="primary"):
        if total_respondidas == 0:
            st.error("Você precisa responder pelo menos uma questão")
        else:
            with st.spinner("Analisando seu desempenho..."):
                resultado = analyzer.analisar_desempenho(
                    respostas_dict=st.session_state.respostas,
                    ano=ano_prova,
                    cor_prova=cor_prova,
                    estado=estado
                )
                if "erro" in resultado:
                    st.error(resultado["erro"])
                else:
                    st.session_state.analise_resultado = resultado
                    st.success("Análise concluída")

with col2:
    if st.button("Limpar", use_container_width=True):
        st.session_state.respostas = {i: "-" for i in range(1, 181)}
        st.session_state.analise_resultado = None
        st.rerun()

st.markdown("---")
st.markdown("## Resultados da Análise")

if st.session_state.analise_resultado is not None:
    resultado = st.session_state.analise_resultado
    st.markdown("### Resumo Geral")
    c1,c2,c3,c4 = st.columns(4)
    with c1:
        st.metric("Acertos Totais", f"{resultado['total_acertos']}/180")
    with c2:
        st.metric("Percentual", f"{resultado['percentual_geral']}%")
    with c3:
        st.metric("Nota Geral", f"{resultado['nota_geral']}")
    with c4:
        if resultado['estado']:
            st.metric("Estado", resultado['estado'])
        else:
            st.metric("Comparação", "Nacional")

    st.info(f"Prova escolhida (melhor match): CO_PROVA_CH={resultado['info_prova']['CO_PROVA_CH']}, CO_PROVA_CN={resultado['info_prova']['CO_PROVA_CN']}, CO_PROVA_LC={resultado['info_prova']['CO_PROVA_LC']}, CO_PROVA_MT={resultado['info_prova']['CO_PROVA_MT']} — matches: {resultado['info_prova']['match_score']}")

    st.markdown("### Desempenho por Área")
    for area_code, area_nome in analyzer.areas_nomes.items():
        with st.expander(f"{area_nome}", expanded=True):
            res_area = resultado['resultados_areas'][area_code]
            a1,a2,a3,a4 = st.columns(4)
            with a1:
                st.metric("Acertos", f"{res_area['acertos']}/{res_area['total_questoes']}")
            with a2:
                st.metric("Percentual", f"{res_area['percentual']:.1f}%")
            with a3:
                st.metric("Nota Estimada", f"{res_area['nota_estimada']}", delta=f"{res_area['diferenca_nacional']:+.1f} vs nacional" if res_area['diferenca_nacional'] is not None else "")
            with a4:
                if res_area['media_regional']:
                    st.metric("Média Regional", f"{res_area['media_regional']}", delta=f"{res_area['diferenca_regional']:+.1f} você")
                else:
                    st.metric("Média Nacional", f"{res_area['media_nacional']}")
            st.progress(res_area['percentual'] / 100)

    melhor_area = max(resultado['resultados_areas'].items(), key=lambda x: x[1]['nota_estimada'])
    pior_area = min(resultado['resultados_areas'].items(), key=lambda x: x[1]['nota_estimada'])
    colL, colR = st.columns(2)
    with colL:
        st.success(f"Melhor: {analyzer.areas_nomes[melhor_area[0]]} — Nota {melhor_area[1]['nota_estimada']}")
    with colR:
        st.warning(f"Pior: {analyzer.areas_nomes[pior_area[0]]} — Nota {pior_area[1]['nota_estimada']}")

elif total_respondidas > 0:
    st.info("Configure o ano e cor da prova acima, preencha o gabarito e clique em 'Gerar Análise de Desempenho'")
else:
    st.info("Preencha o gabarito acima para começar sua análise de desempenho")

# --- Footer ---
st.markdown("---")
st.caption("💡 **Dica:** As notas são estimativas baseadas em médias históricas e podem não refletir exatamente a nota TRI real. Use como referência para seu estudo!")
