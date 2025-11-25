import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import joblib
import os
from collections import OrderedDict

# --- Estilo customizado ---
st.markdown("""
    <style>
        body { background-color: #111111; }
        .stTabs [role="tablist"] button {
            font-size: 16px;
            font-weight: bold;
        }
        div[data-testid="stMetricValue"] {
            font-size: 32px;
            font-weight: bold;
        }
        .big-button button {
            font-size: 18px;
            font-weight: bold;
            padding: 0.6em 2em;
            border-radius: 10px;
        }
        .stRadio > label {
            font-weight: bold;
        }
    </style>
""", unsafe_allow_html=True)

st.title("📈 Predição de Desempenho")

# Mapa de saída
MAP_RESULTADO = {0: "Baixo", 1: "Médio", 2: "Alto"}

# Mapeamento dos tipos de prova (target_col)
MAP_PROVAS = OrderedDict([
    ("Matemática", "NU_NOTA_MT"),
    ("Linguagens e Códigos", "NU_NOTA_LC"),
    ("Ciências da Natureza", "NU_NOTA_CN"),
    ("Ciências Humanas", "NU_NOTA_CH"),
    ("Redação", "NU_NOTA_REDACAO"),
])


# Mock de previsão
def predict_notas(sexo=None, renda=None, esc_pai=None, esc_mae=None, escola=None, idade=None):
    np.random.seed(42)
    return {
        "Linguagens e Códigos": np.random.randint(400, 800),
        "Ciências Humanas": np.random.randint(400, 800),
        "Ciências da Natureza": np.random.randint(400, 800),
        "Matemática": np.random.randint(400, 800),
        "Redação": np.random.randint(400, 1000),
    }


# Inicializa session_state
if "notas" not in st.session_state:
    st.session_state.notas = predict_notas()

default_values = {
    "sexo": "Masculino",
    "idade": 20,
    "renda": "1-3 SM",
    "esc_pai": "Ensino Médio",
    "esc_mae": "Superior",
    "escola": "Pública",
    "internet": "Sim",
    "computador": "Sim"
}

for k, v in default_values.items():
    if k not in st.session_state:
        st.session_state[k] = v


@st.cache_resource
def load_main_model_and_data(target_col):
    """
    Carrega o modelo, os dados de teste e as importâncias das features
    para a prova selecionada. Esta função NÃO pode conter elementos Streamlit.
    """
    data = {}
    base_path = "./prediction_module/src/saved_model"
    os.makedirs(base_path, exist_ok=True)


    model_filename = f"randomForest_{target_col}.pkl"
    model_path = os.path.join(base_path, model_filename)
    csv_x_path = os.path.join(base_path, "analyzer_X_test.csv")
    csv_y_path = os.path.join(base_path, "analyzer_y_test.csv")

    # Carregamentos (Se os arquivos existirem)
    if os.path.exists(model_path):
        data["main_model"] = joblib.load(model_path)
    if os.path.exists(csv_x_path):
        data["X_test"] = pd.read_csv(csv_x_path)
    if os.path.exists(csv_y_path):
        data["y_test"] = pd.read_csv(csv_y_path).squeeze()

    # Carregamento das importâncias (necessário para todas as opções, incluindo GLOBAL)
    importances_filename = f"feature_importances_{target_col}.csv"
    importances_path = os.path.join(base_path, importances_filename)

    if os.path.exists(importances_path):
        data["importances"] = pd.read_csv(importances_path)
    else:
        raise FileNotFoundError(f"Arquivo de importâncias '{importances_filename}' não encontrado.")

    data["target_col"] = target_col
    return data


# Tabs
tab1, tab2, tab3 = st.tabs(["🎯 Simulação de Resultado", "📌 Variáveis Importantes", "🔬 Análise do Modelo Principal"])

# Inicializa o seletor na primeira vez que a página é carregada
if 'prova_seletor' not in st.session_state:
    st.session_state.prova_seletor = list(MAP_PROVAS.keys())[0]

# Obtém o nome da coluna alvo
target_col_selecionado = MAP_PROVAS[st.session_state.prova_seletor]

analysis_data = None
selected_prova_nome = st.session_state.prova_seletor

try:
    analysis_data = load_main_model_and_data(target_col_selecionado)
    st.toast(f"Dados de análise para {selected_prova_nome} carregados! 🎉", icon='✅')

except FileNotFoundError as e:
    # Captura erros de FileNotFoundError aqui. O erro de modelo principal (tab3)
    # é tratado dentro da tab3
    if "importances" in str(e):
        st.error(f"Erro Crítico: Arquivo de importâncias não encontrado para {selected_prova_nome}.")
        st.error(
            f"Verifique se o arquivo necessário existe: './prediction_module/src/saved_model/{os.path.basename(str(e).split(' ')[-1])}'")
    else:
        # Se for erro de modelo/X_test/y_test, permite continuar para o Tab 1
        st.warning(
            f"Aviso: Arquivos de modelo ou teste para {selected_prova_nome} não encontrados, Abas 2 e 3 podem falhar. {e}")
except Exception as e:
    st.error(f"Erro inesperado no carregamento: {e}")

# --- TAB 1 (Simulação de Resultado) ---
with tab1:
    st.info("Preencha os campos socioeconômicos e veja a previsão dinâmica de desempenho em cada área do ENEM.")

    # --- Cards com métricas ---
    st.subheader("📊 Resultado da Predição")
    cards_placeholder = st.empty()


    def render_cards():
        with cards_placeholder:
            cols = st.columns(5)
            for (area, nota), col in zip(st.session_state.notas.items(), cols):
                col.metric(area, nota)


    # Render inicial (sempre uma vez só)
    render_cards()

    # --- Formulário ---
    st.subheader("🧑‍🎓 Dados do Participante")
    with st.form("prediction_form"):
        sexo = st.radio("Sexo", ["Masculino", "Feminino", "Prefiro não informar"],
                        horizontal=True,
                        index=["Masculino", "Feminino", "Prefiro não informar"].index(st.session_state.sexo))

        idade = st.slider("Idade", 0, 100, st.session_state.idade)

        renda = st.radio("Renda Familiar", ["Até 1 SM", "1-3 SM", "3-5 SM", "Mais de 5 SM"],
                         horizontal=True,
                         index=["Até 1 SM", "1-3 SM", "3-5 SM", "Mais de 5 SM"].index(st.session_state.renda))

        col1, col2 = st.columns(2)
        with col1:
            esc_pai = st.select_slider(
                "Escolaridade do Pai",
                options=["Fundamental", "Ensino Médio", "Superior", "Pós-graduação", "Não informado"],
                value=st.session_state.esc_pai
            )
        with col2:
            esc_mae = st.select_slider(
                "Escolaridade da Mãe",
                options=["Fundamental", "Ensino Médio", "Superior", "Pós-graduação", "Não informado"],
                value=st.session_state.esc_mae
            )

        escola = st.radio("Tipo da Escola", ["Pública", "Privada", "Federal"],
                          horizontal=True, index=["Pública", "Privada", "Federal"].index(st.session_state.escola))

        col1, col2 = st.columns(2)
        with col1:
            internet = st.radio("Possui acesso à Internet?", ["Sim", "Não"],
                                horizontal=True, index=["Sim", "Não"].index(st.session_state.internet))
        with col2:
            computador = st.radio("Possui computador?", ["Sim", "Não"],
                                  horizontal=True, index=["Sim", "Não"].index(st.session_state.computador))

        col1, col2 = st.columns(2)
        with col1:
            limpar = st.form_submit_button("🗑️ Limpar")
        with col2:
            submitted = st.form_submit_button("📊 Gerar Nova Previsão")

    # --- Ações dos botões ---
    if submitted:
        st.session_state.update({
            "sexo": sexo,
            "idade": idade,
            "renda": renda,
            "esc_pai": esc_pai,
            "esc_mae": esc_mae,
            "escola": escola,
            "internet": internet,
            "computador": computador,
        })
        st.session_state.notas = predict_notas(sexo, renda, esc_pai, esc_mae, escola, idade)
        render_cards()  # re-renderiza no mesmo placeholder

    if limpar:
        for k, v in default_values.items():
            st.session_state[k] = v
        st.session_state.notas = predict_notas()
        st.rerun()

    # --- Gráfico ---
    st.subheader("📈 Visualização Gráfica")
    df_notas = pd.DataFrame({
        "Área": list(st.session_state.notas.keys()),
        "Nota Prevista": list(st.session_state.notas.values())
    })
    fig = px.bar(df_notas, x="Área", y="Nota Prevista", text="Nota Prevista",
                 color="Área", title="Notas Previstas por Área do ENEM")
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, use_container_width=True)

# --- TAB 2 (Variáveis Importantes) ---
with tab2:
    st.subheader("📌 Importância das Variáveis")

    # Lista de opções apenas para o seletor desta aba
    options_for_tab2 = list(MAP_PROVAS.keys())

    st.selectbox(
        "Selecione o Contexto de Análise:",
        options=options_for_tab2,
        index=options_for_tab2.index(selected_prova_nome),  # Mantém o estado atual
        key='prova_seletor_tab2',
        on_change=st.rerun  # Força o recarregamento ao trocar de prova
    )

    # Atualiza o seletor principal se foi alterado nesta aba
    if st.session_state.prova_seletor_tab2 != st.session_state.prova_seletor:
        st.session_state.prova_seletor = st.session_state.prova_seletor_tab2
        st.rerun()

    st.info(
        f"O gráfico mostra as variáveis que o modelo de predição considerou mais importantes para prever o resultado **{selected_prova_nome}**.")

    if analysis_data and "importances" in analysis_data:
        top_n = 10

        df_importances = analysis_data["importances"].head(top_n).sort_values(by="Importance", ascending=True)

        fig = px.bar(
            df_importances,
            x="Importance",
            y="Feature",
            orientation='h',
            title=f"Top {top_n} Importância das Variáveis para {selected_prova_nome}",
            labels={'Importance': 'Pontuação de Importância (Gini)', 'Feature': 'Variável'},
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        fig.update_layout(xaxis_title="Importância Relativa")
        st.plotly_chart(fig, use_container_width=True)

        # Detalhamento em tabela
        st.markdown("---")
        st.markdown(f"#### 🔍 Detalhamento das Importâncias (Top {top_n})")
        st.dataframe(df_importances.sort_values(by="Importance", ascending=False).reset_index(drop=True))

    else:
        st.warning(
            f"Os dados de importância das variáveis para o contexto **{selected_prova_nome}** não estão disponíveis. Verifique se o arquivo `feature_importances_{target_col_selecionado}.csv` foi salvo corretamente.")

# --- TAB 3 (Análise do Modelo Principal) ---
with tab3:
    st.subheader("🔬 Análise Exploratória do Modelo Principal")

    provas_analise_exclusiva = [k for k in MAP_PROVAS.keys() if MAP_PROVAS[k] ]

    if selected_prova_nome not in provas_analise_exclusiva:
        st.session_state.prova_seletor = provas_analise_exclusiva[0]
        st.rerun()

    st.selectbox(
        "Selecione o Modelo de Prova para Análise:",
        options=provas_analise_exclusiva,
        index=provas_analise_exclusiva.index(selected_prova_nome),  # Mantém o estado atual
        key='prova_seletor_tab3',
        on_change=st.rerun  # Força o recarregamento ao trocar de prova
    )

    # Atualiza o seletor principal se foi alterado nesta aba
    if st.session_state.prova_seletor_tab3 != st.session_state.prova_seletor:
        st.session_state.prova_seletor = st.session_state.prova_seletor_tab3
        st.rerun()

    st.info(
        "Aqui usamos o modelo para fazer previsões de alunos reais do conjunto de teste.")
    st.markdown(f"**Modelo Carregado:** `randomForest_{target_col_selecionado}.pkl` ({selected_prova_nome})")

    if analysis_data and analysis_data.get("target_col") == target_col_selecionado:

        # Verifica se o modelo e os dados de teste foram carregados
        if "main_model" not in analysis_data or "X_test" not in analysis_data or "y_test" not in analysis_data:
            st.warning("Arquivos de modelo principal ou dados de teste não foram carregados. Verifique o diretório.")
        else:
            main_model = analysis_data["main_model"]
            X_test_analyzer = analysis_data["X_test"]
            y_test_analyzer = analysis_data["y_test"]

            # Botão para sortear um aluno
            if st.button("Carregar Aluno Aleatório do Teste", use_container_width=True, key="btn_analise"):
                rand_idx = np.random.randint(0, len(X_test_analyzer))
                st.session_state.analyzer_idx = rand_idx
                # Armazena a coluna alvo do modelo atual para evitar predições cruzadas
                st.session_state.analyzer_col = target_col_selecionado

            # Se um aluno foi sorteado E o modelo for o mesmo, mostra os dados
            if "analyzer_idx" in st.session_state and st.session_state.get("analyzer_col") == target_col_selecionado:
                idx = st.session_state.analyzer_idx
                st.markdown(f"--- \n### 🧑‍🎓 Aluno Sorteado (Índice: {idx})")

                # Pega os dados do aluno
                aluno_x_data = X_test_analyzer.iloc[[idx]]
                aluno_y_real_class = y_test_analyzer.iloc[idx]

                # Faz a predição com o modelo principal
                aluno_y_pred_class = main_model.predict(aluno_x_data)[0]

                # Converte as classes (0,1,2) para labels ("Baixo", "Médio", "Alto")
                pred_label = MAP_RESULTADO[aluno_y_pred_class]
                real_label = MAP_RESULTADO[aluno_y_real_class]

                # Mostra os resultados
                st.markdown("#### Resultado da Predição ")
                cols = st.columns(2)
                cols[0].metric("🎯 Predição do Modelo", pred_label)
                cols[1].metric("✅ Resultado Real", real_label)

                if pred_label == real_label:
                    st.success("O modelo acertou a previsão!")
                else:
                    st.error("O modelo errou a previsão.")

                st.markdown("--- \n#### Dados Completos do Aluno ")
                st.dataframe(aluno_x_data.T)

            elif "analyzer_idx" in st.session_state and st.session_state.get("analyzer_col") != target_col_selecionado:
                st.warning(
                    f"O modelo de previsão mudou para **{selected_prova_nome}**. Clique em **'Carregar Aluno Aleatório do Teste'** para rodar a previsão com o novo modelo.")

    else:
        st.error(
            f"Não foi possível carregar o modelo ou os dados de análise para a prova selecionada ({selected_prova_nome}).")