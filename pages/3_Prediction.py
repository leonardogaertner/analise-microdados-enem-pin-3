import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 🔙 Botão de voltar
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

if st.button("⬅", key="back_button"):
    st.switch_page("app.py")

st.title("📈 Predição de Desempenho")

# Função mock de predição
def predict_notas(sexo=None, renda=None, esc_pai=None, esc_mae=None, escola=None):
    np.random.seed(42)
    return {
        "Linguagens e Códigos": np.random.randint(400, 800),
        "Ciências Humanas": np.random.randint(400, 800),
        "Ciências da Natureza": np.random.randint(400, 800),
        "Matemática": np.random.randint(400, 800),
        "Redação": np.random.randint(400, 1000),
    }

# --- Tabs ---
tab1, tab2 = st.tabs(["🎯 Simulação de Resultado", "📌 Variáveis Importantes"])

# ================= TAB 1 =================
with tab1:
    st.info("Preencha os campos socioeconômicos e veja a previsão dinâmica de desempenho em cada área do ENEM.")

    # Área fixa da tabela
    st.subheader("📊 Resultado da Predição")
    tabela_placeholder = st.empty()

    if "notas" not in st.session_state:
        st.session_state.notas = predict_notas()

    df_notas = pd.DataFrame({
        "Área": list(st.session_state.notas.keys()),
        "Nota Prevista": list(st.session_state.notas.values())
    })
    tabela_placeholder.dataframe(df_notas, hide_index=True, use_container_width=True)

    # Formulário socioeconômico
    st.subheader("🧑‍🎓 Dados do Participante")
    with st.form("prediction_form"):
        sexo = st.selectbox("Sexo", ["Masculino", "Feminino", "Prefiro não informar"])
        renda = st.selectbox("Renda Familiar", ["Até 1 SM", "1-3 SM", "3-5 SM", "Mais de 5 SM"])
        esc_pai = st.selectbox("Escolaridade do Pai", ["Fundamental", "Médio", "Superior", "Não informado"])
        esc_mae = st.selectbox("Escolaridade da Mãe", ["Fundamental", "Médio", "Superior", "Não informado"])
        escola = st.selectbox("Tipo de Escola", ["Pública", "Privada", "Mista"])

        submitted = st.form_submit_button("Gerar Nova Previsão")

    if submitted:
        st.session_state.notas = predict_notas(sexo, renda, esc_pai, esc_mae, escola)

        df_notas = pd.DataFrame({
            "Área": list(st.session_state.notas.keys()),
            "Nota Prevista": list(st.session_state.notas.values())
        })
        tabela_placeholder.dataframe(df_notas, hide_index=True, use_container_width=True)

        st.subheader("📈 Visualização Gráfica")
        fig = px.bar(df_notas, x="Área", y="Nota Prevista", text="Nota Prevista",
                    color="Área", title="Notas Previstas por Área do ENEM")
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

# ================= TAB 2 =================
with tab2:
    st.info("Veja as variáveis que mais impactam no resultado do modelo.")

    variaveis = [
        {"nome": "Renda Familiar", "descricao": "A renda está fortemente relacionada ao acesso a materiais de estudo e cursos preparatórios."},
        {"nome": "Tipo de Escola", "descricao": "Estudantes de escolas privadas, em média, têm acesso a mais recursos de aprendizagem."},
        {"nome": "Escolaridade da Mãe", "descricao": "Pesquisas indicam que o nível de escolaridade da mãe tem alta correlação com o desempenho escolar."},
        {"nome": "Sexo", "descricao": "Diferenças de desempenho entre homens e mulheres são observadas em algumas áreas do ENEM."},
    ]

    cols = st.columns(2)

    for i, var in enumerate(variaveis):
        # Criar uma função dialog única para cada variável
        @st.dialog(var["nome"])
        def abrir_dialogo(v=var):
            st.markdown(f"### {v['nome']}")
            st.write(v["descricao"])
            st.info("🔎 Aqui futuramente poderemos mostrar gráficos explicativos do impacto desta variável.")
            # Exemplo de gráfico fake
            st.bar_chart({"Impacto": np.random.randint(1, 100, size=5)})

        with cols[i % 2]:
            if st.button(var["nome"], use_container_width=True, key=f"btn_{i}"):
                abrir_dialogo()
