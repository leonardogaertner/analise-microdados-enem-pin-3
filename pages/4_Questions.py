import streamlit as st

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

        .nav-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 8px 16px rgba(0,0,0,0.2);
            text-align: center;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            cursor: pointer;
            margin: 20px 0;
            height: 250px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }

        .nav-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 24px rgba(0,0,0,0.3);
        }

        .nav-card-analysis {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }

        .nav-card-performance {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }

        .nav-card-title {
            font-size: 32px;
            font-weight: bold;
            color: white;
            margin-bottom: 15px;
        }

        .nav-card-description {
            font-size: 18px;
            color: rgba(255,255,255,0.9);
            line-height: 1.6;
        }

        .nav-card-icon {
            font-size: 60px;
            margin-bottom: 20px;
        }
    </style>
""", unsafe_allow_html=True)

if st.button("⬅", key="back_button"):
    st.switch_page("app.py")

st.title("📝 Análise de Questões do ENEM")
st.markdown("### Escolha o tipo de análise que deseja realizar")

st.markdown("---")

# Layout com duas colunas para os cards
col1, col2 = st.columns(2)

with col1:
    st.markdown("""
        <div class="nav-card nav-card-analysis">
            <div class="nav-card-icon">📊</div>
            <div class="nav-card-title">Análise de Questões</div>
            <div class="nav-card-description">
                Explore as questões do ENEM por ano, cor e área.
                Analise parâmetros TRI, taxas de acerto e estatísticas detalhadas.
            </div>
        </div>
    """, unsafe_allow_html=True)

    if st.button("Ir para Análise de Questões", key="btn_analysis", use_container_width=True, type="primary"):
        st.switch_page("pages/4_Questions_Analysis.py")

with col2:
    st.markdown("""
        <div class="nav-card nav-card-performance">
            <div class="nav-card-icon">🎯</div>
            <div class="nav-card-title">Análise de Desempenho</div>
            <div class="nav-card-description">
                Preencha seu gabarito e compare seu desempenho com
                médias nacionais e regionais. Veja sua nota estimada!
            </div>
        </div>
    """, unsafe_allow_html=True)

    if st.button("Ir para Análise de Desempenho", key="btn_performance", use_container_width=True, type="primary"):
        st.switch_page("pages/4_Questions_Performance.py")

st.markdown("---")

# Informações adicionais
st.info("""
**💡 Dica:**
- Use **Análise de Questões** para estudar e entender as características das provas anteriores.
- Use **Análise de Desempenho** para simular sua prova e avaliar seu nível de preparo.
""")
