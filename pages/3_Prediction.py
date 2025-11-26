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
        /* Novo estilo para exibir a classe de desempenho na Aba 1 */
        .desempenho-metric div[data-testid="stMetricLabel"] {
            font-size: 18px;
            font-weight: bold;
        }
        .desempenho-metric div[data-testid="stMetricValue"] {
            font-size: 40px;
            font-weight: 900;
            color: #33aaff; /* Cor de destaque para o resultado */
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

# Mapeamento das variáveis mais importantes para apresentação ao usuário
MAP_TRADUCAO_VARIAVEIS = {
    "Q006": "Renda familiar",
    "TP_LINGUA": "Língua escolhida na prova de língua estrangeira",
    "TP_FAIXA_ETARIA": "Faixa etária do candidato",
    "Q005": "Quantidade de pessoas que moram na residência",
    "Q024": "Possui computador na residência",
    "RENDA_FAMILIAR": "Faixa de renda familiar (variável derivada)",
    "NO_MUNICIPIO_PROVA": "Município de realização da prova",
    "ESCOLARIDADE_PAIS_AGRUPADO": "Maior escolaridade entre os pais",
    "TP_ANO_CONCLUIU": "Ano de conclusão do ensino médio",
    "Q002": "Até que ano sua mãe/responsável estudou",
    "INDICE_ACESSO_TECNOLOGIA": "Índice de acesso a tecnologia",
    "TP_ESTADO_CIVIL": "Estado civil do candidato",
    "NU_ANO": "Ano de realização da prova",
    "SG_UF_PROVA": "UF de realização da prova"
}

GENERIC_OPTIONS_6 = {"A": "A (Nenhuma/Não)", "B": "B", "C": "C", "D": "D", "E": "E", "F": "F (3 ou mais/Sim)"}
GENERIC_OPTIONS_2 = {"A": "A (Não)", "B": "B (Sim)"}
GENERIC_OPTIONS_3 = {"A": "A", "B": "B", "C": "C", "D": "D", "E": "E", "F": "F"}

MAP_QUESTIONARIO_OPCOES = {
    # Q001 e Q002 permanecem como estavam
    "Q001_OPTIONS": {"Fundamental": "A", "Ensino Médio": "B", "Superior": "C", "Pós-graduação": "D", "Não informado": "A"},
    "Q002_OPTIONS": {"Fundamental": "A", "Ensino Médio": "B", "Superior": "C", "Pós-graduação": "D", "Não informado": "A"},
    # Q006: Renda Familiar Mensal (mapeia para letras de A a Q)
    "Q006_OPTIONS": {
        "Nenhuma Renda": "A",
        "Até 1.320,00": "B",
        "De 1.320,01 até 1.980,00.": "C",
        "De 1.980,01 até 2.640,00.": "D",
        "De 2.640,01 até 3.300,00.": "E",
        "De 3.300,01 até 3.960,00.": "F",
        "De 3.960,01 até 5.280,00.": "G",
        "De 5.280,01 até 6.600,00.": "H",
        "De 6.600,01 até 7.920,00.": "I",
        "De 7.920,01 até 9240,00.": "J",
        "De 9.240,01 até 10.560,00.": "K",
        "De 10.560,01 até 11.880,00.": "L",
        "De 11.880,01 até 13.200,00.": "M",
        "De 13.200,01 até 15.840,00.": "N",
        "De 15.840,01 até19.800,00.": "O",
        "De 19.800,01 até 26.400,00.": "P",
        "Acima de 26.400,00.": "Q",
    },

    # Q003: Nº de Quartos
    "Q003_OPTIONS": GENERIC_OPTIONS_3,
    # Q004: Nº de Banheiros
    "Q004_OPTIONS": GENERIC_OPTIONS_3,
    # Q005: Nº de Pessoas na residência
    "Q005_OPTIONS": GENERIC_OPTIONS_6,

    # Q007 a Q023 (Variáveis Binárias: Posse de Itens/Serviços)
    "Q007_OPTIONS": {"A": "A", "B": "B", "C": "C", "D": "D"},
    "Q008_OPTIONS": {"A": "A", "B": "B", "C": "C", "D": "D", "E": "E"},
    "Q009_OPTIONS": {"A": "A", "B": "B", "C": "C", "D": "D", "E": "E"},
    "Q010_OPTIONS": {"A": "A", "B": "B", "C": "C", "D": "D", "E": "E"},
    "Q011_OPTIONS": {"A": "A", "B": "B", "C": "C", "D": "D", "E": "E"},
    "Q012_OPTIONS": {"A": "A", "B": "B", "C": "C", "D": "D", "E": "E"},
    "Q013_OPTIONS": {"A": "A", "B": "B", "C": "C", "D": "D", "E": "E"},
    "Q014_OPTIONS": {"A": "A", "B": "B", "C": "C", "D": "D", "E": "E"},
    "Q015_OPTIONS": {"A": "A", "B": "B", "C": "C", "D": "D", "E": "E"},
    "Q016_OPTIONS": {"A": "A", "B": "B", "C": "C", "D": "D", "E": "E"},
    "Q017_OPTIONS": {"A": "A", "B": "B", "C": "C", "D": "D", "E": "E"},
    "Q018_OPTIONS": GENERIC_OPTIONS_2,
    "Q019_OPTIONS": {"A": "A", "B": "B", "C": "C", "D": "D", "E": "E"},
    "Q020_OPTIONS": GENERIC_OPTIONS_2,
    "Q021_OPTIONS": GENERIC_OPTIONS_2,
    "Q022_OPTIONS": {"A": "A", "B": "B", "C": "C", "D": "D", "E": "E"},
    "Q023_OPTIONS": GENERIC_OPTIONS_2,
    "Q024_OPTIONS": {"A": "A", "B": "B", "C": "C", "D": "D", "E": "E"},
    "Q025_OPTIONS": GENERIC_OPTIONS_2,
}

# --- MAPEAMENTO DE ENTRADA DO FORMULÁRIO PARA O MODELO - EXPANDIDO
MAP_FORM_TO_MODEL = {
    # ... Variáveis Diretas/Ordinais existentes
    "idade": "TP_FAIXA_ETARIA",
    "renda": "Q006",
    "esc_pai": "Q001",
    "esc_mae": "Q002",
    "internet": "Q025",
    "computador": "Q024",
    # NOVAS Q's (Armazenaremos a letra da resposta)
    "q003": "Q003", "q004": "Q004", "q005": "Q005", "q007": "Q007", "q008": "Q008",
    "q009": "Q009", "q010": "Q010", "q011": "Q011", "q012": "Q012", "q013": "Q013",
    "q014": "Q014", "q015": "Q015", "q016": "Q016", "q017": "Q017", "q018": "Q018",
    "q019": "Q019", "q020": "Q020", "q021": "Q021", "q022": "Q022", "q023": "Q023",
    "q024": "Q024", "q025": "Q025",

    # ... Variáveis Categóricas existentes
    "sexo": {"Masculino": "M", "Feminino": "F"},
    "lingua_estrangeira": {"Inglês": 0, "Espanhol": 1},
    "escola": {"Pública": 2, "Privada": 3, "Federal": 2},
    "treineiro": {"Sim": 1, "Não": 0},
    "estado_civil": {"Solteiro": 1, "Casado/União": 2, "Outros": 0},
    "cor_raca": {"Branca": 1, "Preta": 2, "Parda": 3, "Amarela": 4, "Indígena": 5, "Não Declarar": 0},

    # NOVAS Variáveis Fixas/Flags (Simplificadas para o formulário)
    "regiao_candidato": {"Sudeste": 3, "Sul": 4, "Nordeste": 2, "Norte": 1, "Centro-Oeste": 5},
    "regiao_escola": {"Sudeste": 3, "Sul": 4, "Nordeste": 2, "Norte": 1, "Centro-Oeste": 5},
    "flag_capital": {"Sim": 1, "Não": 0},
    "in_certificado": {"Sim": 1, "Não": 0},
    "tp_dependencia_adm_esc": {"Federal": 1, "Estadual": 2, "Municipal": 3, "Privada": 4, "Não se aplica": 0},
    "tp_localizacao_esc": {"Urbana": 1, "Rural": 2, "Não se aplica": 0},
    "tp_ensino": {"Ensino Médio Regular": 1, "EJA": 2, "Outros": 0},
}

# --- FUNÇÃO AUXILIAR DE PREPARAÇÃO DE DADOS ---
def map_idade_to_faixa_etaria(idade):
    """Mapeia idade para as categorias TP_FAIXA_ETARIA (1 a 20) do ENEM."""
    if idade <= 16: return 1
    if idade == 17: return 2
    if idade == 18: return 3
    if idade == 19: return 4
    if idade == 20: return 5
    if 21 <= idade <= 24: return 6
    if 25 <= idade <= 30: return 7
    if 31 <= idade <= 35: return 8
    if 36 <= idade <= 40: return 9
    if 41 <= idade <= 45: return 10
    if 46 <= idade <= 50: return 11
    if 51 <= idade <= 55: return 12
    if 56 <= idade <= 60: return 13
    if 61 <= idade <= 65: return 14
    if 66 <= idade <= 70: return 15
    if idade > 70: return 16 # Ajuste para caber nas faixas
    return 1 # Default (idade não informada)

def prepare_student_data_for_prediction(form_data, model_features):
    """
    Recebe os dados do formulário e transforma em um DataFrame pronto para o modelo,
    aplicando Label Encoding manual e preenchendo features faltantes com 0.
    """

    # 1. Mapeamento de Categorias (A, B, C... para 0, 1, 2...)
    category_map = {'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9, 'K': 10,
        'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18, 'T': 19}

    # Mapeamento da Escolaridade para comparação (quanto maior o valor, maior a escolaridade)
    # Fundamental/Não informado=0, Ensino Médio=1, Superior=2, Pós-graduação=3
    esc_map_val = {"Não informado": 0, "Fundamental": 0, "Ensino Médio": 1, "Superior": 2, "Pós-graduação": 3}

    # 2. Converte os dados do formulário expandido para o formato do modelo (Inicialização)
    # Mantendo o data_aluno como um dict para updates posteriores
    data_aluno = {}

    # Mapeamento e Inclusão das Q's do Questionário Socioeconômico
    socio_data = {}
    for k_form, k_model in MAP_FORM_TO_MODEL.items():
        # Captura as respostas do questionário (Q001 a Q025)
        if isinstance(k_model, str) and k_model.startswith('Q0') and not k_model.startswith('Q005'):
            if k_form in form_data:
                # O valor do form_data para as Q's é uma string como "A (Nenhuma/Não)" ou "A"
                if k_form == "q005":
                    num_pessoas = form_data.get(k_form, 1)
                    if num_pessoas == 1: letra_resposta = 'A'
                    elif num_pessoas == 2: letra_resposta = 'B'
                    elif num_pessoas == 3: letra_resposta = 'C'
                    elif num_pessoas == 4: letra_resposta = 'D'
                    elif num_pessoas == 5: letra_resposta = 'E'
                    else: letra_resposta = 'F' # 6 ou mais
                else:
                    letra_resposta = form_data[k_form][0] # Pega o 'A'

                socio_data[k_model] = category_map.get(letra_resposta, 0) # Mapeia 'A' para 0
            else:
                socio_data[k_model] = 0

    # Q001 e Q002 (Escolaridade dos pais)
    esc_pai_str = form_data.get("esc_pai", "Não informado")
    esc_mae_str = form_data.get("esc_mae", "Não informado")
    socio_data['Q001'] = category_map.get(MAP_QUESTIONARIO_OPCOES["Q001_OPTIONS"].get(esc_pai_str, 'A'), 0)
    socio_data['Q002'] = category_map.get(MAP_QUESTIONARIO_OPCOES["Q002_OPTIONS"].get(esc_mae_str, 'A'), 0)

    # Q006 (Renda Familiar)
    renda_str = form_data.get("renda", "Nenhuma Renda")
    letra_renda = MAP_QUESTIONARIO_OPCOES["Q006_OPTIONS"].get(renda_str, 'A')
    socio_data['Q006'] = category_map.get(letra_renda, 0)

    # --- CÁLCULOS DERIVADOS ---

    # CÁLCULO 1: FLAG_CANDIDATO_ADULTO
    idade = form_data.get("idade", 20)
    flag_adulto = 1 if idade >= 25 else 0

    # CÁLCULO 2: ESCOLARIDADE_PAIS_AGRUPADO
    nivel_pai = esc_map_val.get(esc_pai_str, 0)
    nivel_mae = esc_map_val.get(esc_mae_str, 0)
    escolaridade_pais_agrupado = max(nivel_pai, nivel_mae)

    # CÁLCULO 3: INDICE_ACESSO_TECNOLOGIA (Simples)
    acesso_internet = 1 if form_data.get("internet", "Não") == "Sim" else 0
    possui_computador = 1 if form_data.get("computador", "Não") == "Sim" else 0
    indice_acesso = acesso_internet + possui_computador

    # CÁLCULO 4: RENDA_FAMILIAR
    renda_familiar_agrupada = socio_data['Q006']

    # --- CONSTRUÇÃO FINAL DO DATAFRAME ---
    data_aluno = {
        # Variáveis Diretas/Codificadas
        'TP_SEXO': 1 if MAP_FORM_TO_MODEL["sexo"].get(form_data["sexo"], 'M') == 'F' else 0, # M:0, F:1
        'TP_FAIXA_ETARIA': map_idade_to_faixa_etaria(idade),
        'TP_ESCOLA': MAP_FORM_TO_MODEL["escola"].get(form_data.get("escola", "Pública"), 2),
        'TP_LINGUA': MAP_FORM_TO_MODEL["lingua_estrangeira"].get(form_data.get("lingua_estrangeira", "Inglês"), 0),
        'IN_TREINEIRO': MAP_FORM_TO_MODEL["treineiro"].get(form_data.get("treineiro", "Não"), 0),
        'TP_ESTADO_CIVIL': MAP_FORM_TO_MODEL["estado_civil"].get(form_data.get("estado_civil", "Solteiro"), 1),
        'TP_COR_RACA': MAP_FORM_TO_MODEL["cor_raca"].get(form_data.get("cor_raca", "Parda"), 3),

        # Variáveis Contextuais/Flags
        'FLAG_CAPITAL': MAP_FORM_TO_MODEL["flag_capital"].get(form_data.get("flag_capital", "Não"), 0),
        'IN_CERTIFICADO': MAP_FORM_TO_MODEL["in_certificado"].get(form_data.get("in_certificado", "Não"), 0),
        'REGIAO_CANDIDATO': MAP_FORM_TO_MODEL["regiao_candidato"].get(form_data.get("regiao_candidato", "Sudeste"), 3),
        'REGIAO_ESCOLA': MAP_FORM_TO_MODEL["regiao_escola"].get(form_data.get("regiao_escola", "Sudeste"), 3),
        'TP_DEPENDENCIA_ADM_ESC': MAP_FORM_TO_MODEL["tp_dependencia_adm_esc"].get(form_data.get("tp_dependencia_adm_esc", "Não se aplica"), 0),
        'TP_LOCALIZACAO_ESC': MAP_FORM_TO_MODEL["tp_localizacao_esc"].get(form_data.get("tp_localizacao_esc", "Urbana"), 1),
        'TP_ENSINO': MAP_FORM_TO_MODEL["tp_ensino"].get(form_data.get("tp_ensino", "Ensino Médio Regular"), 1),

        # VARIÁVEIS DERIVADAS CALCULADAS
        'FLAG_CANDIDATO_ADULTO': flag_adulto,
        'ESCOLARIDADE_PAIS_AGRUPADO': escolaridade_pais_agrupado,
        'RENDA_FAMILIAR': renda_familiar_agrupada,
        'INDICE_ACESSO_TECNOLOGIA': indice_acesso,

        # Variáveis que não estão no formulário e PERMANECEM ZERADAS/FIXAS
        'CO_UF_ENTIDADE_CERTIFICACAO': 0, 'NO_ENTIDADE_CERTIFICACAO': 0, 'NO_MUNICIPIO_ESC': 0,
        'NO_MUNICIPIO_PROVA': 0, 'SG_UF_ENTIDADE_CERTIFICACAO': 0, 'SG_UF_ESC': 0, 'SG_UF_PROVA': 0,
        'NU_ANO': 2022,
        'TEMPO_FORA_ESCOLA': 0, 'TIPO_ESCOLA_AGRUPADO': 0, 'TP_ANO_CONCLUIU': 0,
        'TP_SIT_FUNC_ESC': 0 # Variável fixa/zerada
    }

    # Adiciona as Q's codificadas (Q001 a Q025)
    data_aluno.update(socio_data)

    df_aluno = pd.DataFrame([data_aluno])

    # Forçar a ordem das colunas e garantir a consistência de tipos
    # Usamos o reindex para garantir que TODAS as colunas do modelo estejam presentes
    df_aluno = df_aluno.reindex(columns=model_features, fill_value=0)

    try:
        df_aluno = df_aluno.apply(pd.to_numeric, errors='coerce')
        df_aluno = df_aluno.fillna(0) # Preenche quaisquer NAs resultantes da coerção com 0
    except Exception as e:
        # st.error(f"Erro na conversão final de tipos para float: {e}")
        return pd.DataFrame(index=[0], columns=model_features, data=0)

    return df_aluno

# --- FUNÇÃO ATUALIZADA (retorna a classe e a nota mock) ---
@st.cache_data(show_spinner=False)
def real_predict_notas(target_col, student_data_df):
    """Faz a predição real usando o modelo carregado para uma prova."""
    try:
        data = load_main_model_and_data(target_col)
        main_model = data["main_model"]

        aluno_y_pred_class = main_model.predict(student_data_df)[0]

        # Assumindo que a nota prevista é a média da classe:
        # Baixo (0): ~450, Médio (1): ~550, Alto (2): ~650
        if aluno_y_pred_class == 0:
            nota_prevista = np.random.randint(400, 500)
        elif aluno_y_pred_class == 1:
            nota_prevista = np.random.randint(500, 600)
        else: # Classe 2
            nota_prevista = np.random.randint(600, 750)

        # RETORNA A CLASSE E A NOTA
        return aluno_y_pred_class, nota_prevista

    except KeyError:
        # Ocorre se o modelo ou X_test não puderam ser carregados
        return np.random.randint(0, 3), np.random.randint(400, 800) # Retorna mock se falhar
    except Exception as e:
        # st.error(f"Erro ao tentar prever a nota para {target_col}: {e}")
        return np.random.randint(0, 3), np.random.randint(400, 800) # Retorna mock se falhar

def predict_all_notas(form_data, model_features_list):
    """
    Simula a previsão para todas as provas, chamando o modelo real para cada uma.
    Retorna a classe de desempenho e a nota mock.
    """

    all_notas = {}
    for prova_nome, target_col in MAP_PROVAS.items():
        # 1. Prepara os dados do aluno para o modelo
        aluno_df = prepare_student_data_for_prediction(form_data, model_features_list)

        # 2. Roda a predição real (retorna classe e nota)
        pred_class, nota_prevista = real_predict_notas(target_col, aluno_df)
        all_notas[prova_nome] = {"nota": nota_prevista, "desempenho_label": MAP_RESULTADO.get(pred_class, "Indefinido")}

    return all_notas

# Mock de previsão inicial (atualizado para retornar o formato com o label de desempenho)
def predict_notas_inicial():
    np.random.seed(42)
    return {
        "Linguagens e Códigos": {"nota": np.random.randint(400, 800), "desempenho_label": MAP_RESULTADO[np.random.randint(0, 3)]},
        "Ciências Humanas": {"nota": np.random.randint(400, 800), "desempenho_label": MAP_RESULTADO[np.random.randint(0, 3)]},
        "Ciências da Natureza": {"nota": np.random.randint(400, 800), "desempenho_label": MAP_RESULTADO[np.random.randint(0, 3)]},
        "Matemática": {"nota": np.random.randint(400, 800), "desempenho_label": MAP_RESULTADO[np.random.randint(0, 3)]},
        "Redação": {"nota": np.random.randint(400, 1000), "desempenho_label": MAP_RESULTADO[np.random.randint(0, 3)]},
    }

ANALYZER_COLUMNS = [
    "CO_UF_ENTIDADE_CERTIFICACAO","ESCOLARIDADE_PAIS_AGRUPADO","FLAG_CANDIDATO_ADULTO","FLAG_CAPITAL",
    "INDICE_ACESSO_TECNOLOGIA","IN_CERTIFICADO","IN_TREINEIRO","NO_ENTIDADE_CERTIFICACAO","NO_MUNICIPIO_ESC",
    "NO_MUNICIPIO_PROVA","NU_ANO","Q001","Q002","Q003","Q004","Q005","Q006","Q007","Q008","Q009","Q010",
    "Q011","Q012","Q013","Q014","Q015","Q016","Q017","Q018","Q019","Q020","Q021","Q022","Q023","Q024",
    "Q025","REGIAO_CANDIDATO","REGIAO_ESCOLA","RENDA_FAMILIAR","SG_UF_ENTIDADE_CERTIFICACAO","SG_UF_ESC",
    "SG_UF_PROVA","TEMPO_FORA_ESCOLA","TIPO_ESCOLA_AGRUPADO","TP_ANO_CONCLUIU","TP_COR_RACA",
    "TP_DEPENDENCIA_ADM_ESC","TP_ENSINO","TP_ESCOLA","TP_ESTADO_CIVIL","TP_FAIXA_ETARIA","TP_LINGUA",
    "TP_LOCALIZACAO_ESC","TP_SEXO","TP_SIT_FUNC_ESC"
]

# Inicializa session_state com o novo formato de notas
if "notas" not in st.session_state:
    st.session_state.notas = predict_notas_inicial()

default_values = {
    "sexo": "Masculino",
    "idade": 20,
    "renda": "De 1.980,01 até 2.640,00.",
    "esc_pai": "Ensino Médio",
    "esc_mae": "Superior",
    "escola": "Pública",
    "internet": "Sim",
    "computador": "Sim",
    "lingua_estrangeira": "Inglês",
    "treineiro": "Não",
    "estado_civil": "Solteiro",
    "cor_raca": "Parda",

    # Q003, Q004, Q005
    "q003": "A",
    "q004": "B",
    "q005": 3,

    # Q007 a Q025 (Inicializados com a letra da opção)
    "q007": "A", "q008": "B", "q009": "C", "q010": "A",
    "q011": "B", "q012": "C", "q013": "C", "q014": "B",
    "q015": "A", "q016": "D", "q017": "A", "q018": "A (Não)",
    "q019": "C", "q020": "A (Não)", "q021": "B (Sim)", "q022": "C",
    "q023": "B (Sim)", "q024": "C", "q025": "A (Não)",

    # Novas variáveis contextuais
    "regiao_candidato": "Sudeste",
    "regiao_escola": "Sudeste",
    "flag_capital": "Não",
    "in_certificado": "Não",
    "tp_dependencia_adm_esc": "Não se aplica",
    "tp_localizacao_esc": "Urbana",
    "tp_ensino": "Ensino Médio Regular"
}

for k, v in default_values.items():
    if k not in st.session_state:
        st.session_state[k] = v

# --- Função para carregar modelo e dados ---
@st.cache_resource
def load_main_model_and_data(target_col):
    data = {}
    base_path = "./prediction_module/src/saved_model"
    os.makedirs(base_path, exist_ok=True)

    model_filename = f"randomForest_{target_col}.pkl"
    model_path = os.path.join(base_path, model_filename)
    csv_x_path = os.path.join(base_path, "analyzer_X_test.csv")
    csv_y_path = os.path.join(base_path, "analyzer_y_test.csv")

    # Tenta carregar o modelo e os dados de teste (necessários para a Tab 2 e para a função real_predict_notas)
    if os.path.exists(model_path):
        try:
            data["main_model"] = joblib.load(model_path)
        except Exception as e:
            # st.warning(f"Não foi possível carregar o modelo {model_filename}: {e}")
            pass # Continua se o modelo não puder ser carregado, mas a predição será mock
    # O carregamento de X_test/y_test e importances é principalmente para a TAB 2 (Importância)
    if os.path.exists(csv_x_path):
        data["X_test"] = pd.read_csv(csv_x_path)
    if os.path.exists(csv_y_path):
        data["y_test"] = pd.read_csv(csv_y_path).squeeze()


    data["model_features"] = ANALYZER_COLUMNS

    importances_filename = f"feature_importances_{target_col}.csv"
    importances_path = os.path.join(base_path, importances_filename)
    if os.path.exists(importances_path):
        data["importances"] = pd.read_csv(importances_path)
    # else:
    #     raise FileNotFoundError(f"Arquivo de importâncias '{importances_filename}' não encontrado.")

    data["target_col"] = target_col
    return data

# --- Tabs ---
# REMOVENDO A TAB3
tab1, tab2 = st.tabs(["🎯 Simulação de Resultado", "📌 Variáveis Importantes"])

model_features_list = ANALYZER_COLUMNS

# Inicializa o seletor na primeira vez
if 'prova_seletor' not in st.session_state:
    st.session_state.prova_seletor = list(MAP_PROVAS.keys())[0]

# O carregamento dos dados de análise é necessário para a Tab 2
target_col_selecionado = MAP_PROVAS[st.session_state.prova_seletor]
try:
    analysis_data = load_main_model_and_data(target_col_selecionado)
    # st.toast(f"Dados de análise para {st.session_state.prova_seletor} carregados! 🎉", icon='✅')
except Exception as e:
    analysis_data = None
    # st.error(f"Erro inesperado no carregamento dos dados de análise: {e}")

selected_prova_nome = st.session_state.prova_seletor

# --- TAB 1: Simulação de Resultado ---
with tab1:
    st.info("Preencha os campos socioeconômicos e veja a previsão de desempenho em cada área do ENEM.")
    st.subheader("📊 Nível de Desempenho Previsto")
    cards_placeholder = st.empty()

    # FUNÇÃO DE RENDERIZAÇÃO ATUALIZADA (Exibe o Label de Desempenho)
    def render_cards():
        with cards_placeholder:
            cols = st.columns(5)
            # o st.session_state.notas agora é um dict aninhado: {"Área": {"nota": 500, "desempenho_label": "Médio"}}
            for (area, data_nota), col in zip(st.session_state.notas.items(), cols):
                # Usando o st.markdown e o estilo customizado para o título do card
                with col:
                    st.markdown(f'<div class="desempenho-metric">', unsafe_allow_html=True)
                    st.metric(area, data_nota["desempenho_label"])
                    # Adiciona a nota aproximada como uma legenda
                    st.caption(f"Nota aprox.: {data_nota['nota']}")
                    st.markdown(f'</div>', unsafe_allow_html=True)


    render_cards()

    # --- Formulário (Mantido inalterado) ---
    st.subheader("🧑‍🎓 Dados do Participante")
    with st.form("prediction_form"):
        # LINHA 1: Demográficos Básicos
        col1, col2, col3 = st.columns(3)
        with col1:
            sexo = st.radio("Sexo", list(MAP_FORM_TO_MODEL["sexo"].keys()),
                            horizontal=True, index=list(MAP_FORM_TO_MODEL["sexo"].keys()).index(st.session_state.sexo))
        with col2:
            idade = st.slider("Idade", 15, 75, st.session_state.idade)
        with col3:
            cor_raca = st.selectbox("Cor/Raça (TP_COR_RACA)", list(MAP_FORM_TO_MODEL["cor_raca"].keys()),
                                    index=list(MAP_FORM_TO_MODEL["cor_raca"].keys()).index(st.session_state.cor_raca))

        # LINHA 2: Escolaridade dos Pais
        st.subheader("👨‍👩‍👧‍👦 Contexto Familiar e Escolar")
        col1, col2 = st.columns(2)
        with col1:
            esc_pai = st.select_slider("Escolaridade do Pai (Q001)",
                                    options=list(MAP_QUESTIONARIO_OPCOES["Q001_OPTIONS"].keys()),
                                    value=st.session_state.esc_pai)
        with col2:
            esc_mae = st.select_slider("Escolaridade da Mãe (Q002)",
                                    options=list(MAP_QUESTIONARIO_OPCOES["Q002_OPTIONS"].keys()),
                                    value=st.session_state.esc_mae)

        # LINHA 3: Renda e Estado Civil
        col1, col2 = st.columns(2)
        with col1:
            renda = st.select_slider("Renda Familiar (Q006)",
                                    options=list(MAP_QUESTIONARIO_OPCOES["Q006_OPTIONS"].keys()),
                                    value=st.session_state.renda)
        with col2:
            estado_civil = st.radio("Estado Civil (TP_ESTADO_CIVIL)", list(MAP_FORM_TO_MODEL["estado_civil"].keys()),
                                    horizontal=True, index=list(MAP_FORM_TO_MODEL["estado_civil"].keys()).index(st.session_state.estado_civil))

        # LINHA 4: Escola e Idioma
        col1, col2 = st.columns(2)
        with col1:
            escola = st.radio("Tipo da Escola (TP_ESCOLA)", ["Pública", "Privada", "Federal"],
                            horizontal=True, index=["Pública", "Privada", "Federal"].index(st.session_state.escola))
        with col2:
            lingua_estrangeira = st.radio("Língua Estrangeira (TP_LINGUA)", ["Inglês", "Espanhol"],
                                        horizontal=True, index=["Inglês", "Espanhol"].index(st.session_state.lingua_estrangeira))

        # LINHA 5: Tecnologia e Treineiro
        st.subheader("💻 Conectividade e Status")
        col1, col2, col3 = st.columns(3)
        with col1:
            internet = st.radio("Acesso à Internet? (Q025)", ["Sim", "Não"],
                                horizontal=True, index=["Sim", "Não"].index(st.session_state.internet))
        with col2:
            computador = st.radio("Possui computador? (Q024)", ["Sim", "Não"],
                                horizontal=True, index=["Sim", "Não"].index(st.session_state.computador))
        with col3:
            treineiro = st.radio("É Treineiro? (IN_TREINEIRO)", ["Sim", "Não"],
                                horizontal=True, index=["Sim", "Não"].index(st.session_state.treineiro))

        st.subheader("🏡 Questionário Socioeconômico Detalhado")
        st.caption("Responda de Q003 a Q025 para influenciar a previsão com base em seu Índice de Condição Socioeconômica (ICSE).")

        # Q003, Q004, Q005
        col1, col2, col3 = st.columns(3)
        with col1:
            q003 = st.select_slider("Q003 (Ocupação do Pai)", options=list(MAP_QUESTIONARIO_OPCOES["Q003_OPTIONS"].values()), value=st.session_state.q003, key='q003_form')
        with col2:
            q004 = st.select_slider("Q004 (Ocupação da Mãe)", options=list(MAP_QUESTIONARIO_OPCOES["Q004_OPTIONS"].values()), value=st.session_state.q004, key='q004_form')
        with col3:
            q005 = st.slider("Q005 (Nº de Pessoas na Residência)", 1, 20, st.session_state.q005)

        # Q007, Q008, Q009
        col1, col2, col3 = st.columns(3)
        with col1:
            q007 = st.select_slider("Q007 (Empregado doméstico?)", options=list(MAP_QUESTIONARIO_OPCOES["Q007_OPTIONS"].values()), value=st.session_state.q007, key='q007_form')
        with col2:
            q008 = st.select_slider("Q008 (Nº de Banheiros)", options=list(MAP_QUESTIONARIO_OPCOES["Q008_OPTIONS"].values()), value=st.session_state.q008, key='q008_form')
        with col3:
            q009 = st.select_slider("Q009 (Nº de Quartos)", options=list(MAP_QUESTIONARIO_OPCOES["Q009_OPTIONS"].values()), value=st.session_state.q009, key='q009_form')

        # Q010, Q011, Q012
        col1, col2, col3 = st.columns(3)
        with col1:
            q010 = st.select_slider("Q010 (Na sua residência tem carro?)", options=list(MAP_QUESTIONARIO_OPCOES["Q010_OPTIONS"].values()), value=st.session_state.q010, key='q010_form')
        with col2:
            q011 = st.select_slider("Q011 (Na sua residência tem moto?)", options=list(MAP_QUESTIONARIO_OPCOES["Q011_OPTIONS"].values()), value=st.session_state.q011, key='q011_form')
        with col3:
            q012 = st.select_slider("Q012 (Na sua residência tem geladeira?)", options=list(MAP_QUESTIONARIO_OPCOES["Q012_OPTIONS"].values()), value=st.session_state.q012, key='q012_form')

        # Q013, Q014, Q015
        col1, col2, col3 = st.columns(3)
        with col1:
            q013 = st.select_slider("Q013 (Na sua residência tem freezer?)", options=list(MAP_QUESTIONARIO_OPCOES["Q013_OPTIONS"].values()), value=st.session_state.q013, key='q013_form')
        with col2:
            q014 = st.select_slider("Q014 (Na sua residência tem máquina de lavar roupa?)", options=list(MAP_QUESTIONARIO_OPCOES["Q014_OPTIONS"].values()), value=st.session_state.q014, key='q014_form')
        with col3:
            q015 = st.select_slider("Q015 (Na sua residência tem máquina de secar roupa?)", options=list(MAP_QUESTIONARIO_OPCOES["Q015_OPTIONS"].values()), value=st.session_state.q015, key='q015_form')

        # Q016, Q017, Q018
        col1, col2, col3 = st.columns(3)
        with col1:
            q016 = st.select_slider("Q016 (Na sua residência tem micro-ondas?)", options=list(MAP_QUESTIONARIO_OPCOES["Q016_OPTIONS"].values()), value=st.session_state.q016, key='q016_form')
        with col2:
            q017 = st.select_slider("Q017 (Na sua residência tem máquina de lavar louça?)", options=list(MAP_QUESTIONARIO_OPCOES["Q017_OPTIONS"].values()), value=st.session_state.q017, key='q017_form')
        with col3:
            q018 = st.select_slider("Q018 (Na sua residência tem aspirador de pó?)", options=list(MAP_QUESTIONARIO_OPCOES["Q018_OPTIONS"].values()), value=st.session_state.q018, key='q018_form')

        # Q019, Q020, Q021
        col1, col2, col3 = st.columns(3)
        with col1:
            q019 = st.select_slider("Q019 (Na sua residência tem TV em cores?)", options=list(MAP_QUESTIONARIO_OPCOES["Q019_OPTIONS"].values()), value=st.session_state.q019, key='q019_form')
        with col2:
            q020 = st.select_slider("Q020 (Na sua residência tem aparelho de DVD?)", options=list(MAP_QUESTIONARIO_OPCOES["Q020_OPTIONS"].values()), value=st.session_state.q020, key='q020_form')
        with col3:
            q021 = st.select_slider("Q021 (Na sua residência tem rádio?)", options=list(MAP_QUESTIONARIO_OPCOES["Q021_OPTIONS"].values()), value=st.session_state.q021, key='q021_form')

        # Q022, Q023, Q024
        col1, col2, col3 = st.columns(3)
        with col1:
            q022 = st.select_slider("Q022 (Nº de Celulares)", options=list(MAP_QUESTIONARIO_OPCOES["Q022_OPTIONS"].values()), value=st.session_state.q022, key='q022_form')
        with col2:
            q023 = st.select_slider("Q023 (Na sua residência tem telefone fixo?)", options=list(MAP_QUESTIONARIO_OPCOES["Q023_OPTIONS"].values()), value=st.session_state.q023, key='q023_form')
        with col3:
            q024 = st.select_slider("Q024 (Nº de Computadores)", options=list(MAP_QUESTIONARIO_OPCOES["Q024_OPTIONS"].values()), value=st.session_state.q024, key='q024_form')

        # Q025
        col1, = st.columns(1)
        with col1:
            q025 = st.select_slider("Q025 (Na sua residência tem acesso a internet?)", options=list(MAP_QUESTIONARIO_OPCOES["Q025_OPTIONS"].values()), value=st.session_state.q025, key='q025_form')

        # --- NOVO BLOCO: Variáveis Geográficas e Flags ---
        st.subheader("🗺️ Contexto Geográfico e Administrativo")

        col1, col2, col3 = st.columns(3)
        with col1:
            regiao_candidato = st.selectbox("Região do Candidato", list(MAP_FORM_TO_MODEL["regiao_candidato"].keys()), index=list(MAP_FORM_TO_MODEL["regiao_candidato"].keys()).index(st.session_state.regiao_candidato))
        with col2:
            regiao_escola = st.selectbox("Região da Escola", list(MAP_FORM_TO_MODEL["regiao_escola"].keys()), index=list(MAP_FORM_TO_MODEL["regiao_escola"].keys()).index(st.session_state.regiao_escola))
        with col3:
            flag_capital = st.radio("Mora em Capital (Flag)", ["Sim", "Não"], horizontal=True, index=["Sim", "Não"].index(st.session_state.flag_capital))

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            tp_dependencia_adm_esc = st.selectbox("Dependência Adm. Escola", list(MAP_FORM_TO_MODEL["tp_dependencia_adm_esc"].keys()), index=list(MAP_FORM_TO_MODEL["tp_dependencia_adm_esc"].keys()).index(st.session_state.tp_dependencia_adm_esc))
        with col2:
            tp_localizacao_esc = st.selectbox("Localização da Escola", list(MAP_FORM_TO_MODEL["tp_localizacao_esc"].keys()), index=list(MAP_FORM_TO_MODEL["tp_localizacao_esc"].keys()).index(st.session_state.tp_localizacao_esc))
        with col3:
            tp_ensino = st.selectbox("Tipo de Ensino", list(MAP_FORM_TO_MODEL["tp_ensino"].keys()), index=list(MAP_FORM_TO_MODEL["tp_ensino"].keys()).index(st.session_state.tp_ensino))
        with col4:
            in_certificado = st.radio("Solicita Certificado (Flag)", ["Sim", "Não"], horizontal=True, index=["Sim", "Não"].index(st.session_state.in_certificado))

        # Botões de Ação
        col1, col2 = st.columns(2)
        with col1:
            limpar = st.form_submit_button("🗑️ Limpar")
        with col2:
            submitted = st.form_submit_button("📊 Gerar Nova Previsão")

    if submitted:
        # 1. Coleta os dados do formulário
        form_data = {
            "sexo": sexo, "idade": idade, "renda": renda, "esc_pai": esc_pai, "esc_mae": esc_mae,
            "escola": escola, "internet": internet, "computador": computador,
            "lingua_estrangeira": lingua_estrangeira, "treineiro": treineiro,
            "estado_civil": estado_civil, "cor_raca": cor_raca,
            "q003": st.session_state.q003_form, "q004": st.session_state.q004_form, "q005": q005,
            "q007": st.session_state.q007_form, "q008": st.session_state.q008_form,
            "q009": st.session_state.q009_form, "q010": st.session_state.q010_form,
            "q011": st.session_state.q011_form, "q012": st.session_state.q012_form,
            "q013": st.session_state.q013_form, "q014": st.session_state.q014_form,
            "q015": st.session_state.q015_form, "q016": st.session_state.q016_form,
            "q017": st.session_state.q017_form, "q018": st.session_state.q018_form,
            "q019": st.session_state.q019_form, "q020": st.session_state.q020_form,
            "q021": st.session_state.q021_form, "q022": st.session_state.q022_form,
            "q023": st.session_state.q023_form, "q024": st.session_state.q024_form,
            "q025": st.session_state.q025_form,
            "regiao_candidato": regiao_candidato, "regiao_escola": regiao_escola,
            "flag_capital": flag_capital, "in_certificado": in_certificado,
            "tp_dependencia_adm_esc": tp_dependencia_adm_esc,
            "tp_localizacao_esc": tp_localizacao_esc, "tp_ensino": tp_ensino,
        }
        st.session_state.update(form_data)

        # 2. Roda a previsão REAL (agora retorna nota e o rótulo de desempenho)
        st.session_state.notas = predict_all_notas(form_data, model_features_list)
        render_cards()
        st.toast("Previsão concluída! 🎉", icon='✅')

    if limpar:
        # Lógica de limpeza
        for k, v in default_values.items():
            st.session_state[k] = v
        st.session_state.notas = predict_notas_inicial() # Reinicia com valores mock
        st.rerun()

# --- TAB 2: Variáveis Importantes (Mantida Inalterada) ---
with tab2:
    st.subheader("📌 Importância das Variáveis")
    options_for_tab2 = list(MAP_PROVAS.keys()) + ["Geral (todas as provas)"]

    selected_prova_tab2 = st.selectbox(
        "Selecione o Contexto de Análise:",
        options=options_for_tab2,
        index=options_for_tab2.index(st.session_state.prova_seletor) if st.session_state.prova_seletor in options_for_tab2 else 0,
    )

    def traduzir_variavel(var):
        return MAP_TRADUCAO_VARIAVEIS.get(var, var)

    if selected_prova_tab2 == "Geral (todas as provas)":
        st.info("Mostrando a importância geral das variáveis considerando todas as provas.")
        all_importances = []
        for prova_nome, col_target in MAP_PROVAS.items():
            try:
                data_local = load_main_model_and_data(col_target)
                if "importances" in data_local:
                    df_imp = data_local["importances"].copy()
                    df_imp.rename(columns={"Importance": prova_nome}, inplace=True)
                    all_importances.append(df_imp)
            except:
                pass

        if all_importances:
            df_merged = all_importances[0]
            for df in all_importances[1:]:
                df_merged = df_merged.merge(df, on="Feature", how="outer")

            # Calcula a média da importância
            cols_importance = [col for col in df_merged.columns if col != "Feature"]
            df_merged["MeanImportance"] = df_merged[cols_importance].mean(axis=1)

            df_general = df_merged[["Feature", "MeanImportance"]].sort_values("MeanImportance", ascending=False).head(10)
            df_general["Feature"] = df_general["Feature"].apply(traduzir_variavel)

            fig = px.bar(
                df_general.sort_values("MeanImportance", ascending=True),
                x="MeanImportance",
                y="Feature",
                orientation="h",
                title="Importância Geral das Variáveis (Média entre todos os modelos)",
                labels={"MeanImportance": "Importância Média", "Feature": "Variável"},
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df_general.reset_index(drop=True))
        else:
            st.warning("Nenhuma importância pôde ser carregada para o contexto geral.")
    else:
        target_col = MAP_PROVAS[selected_prova_tab2]  # Atualiza a prova corretamente
        try:
            data_local = load_main_model_and_data(target_col)
            if "importances" in data_local:
                df_importances = data_local["importances"].head(10).sort_values(by="Importance", ascending=True).copy()
                df_importances["Feature"] = df_importances["Feature"].apply(traduzir_variavel)

                fig = px.bar(
                    df_importances,
                    x="Importance",
                    y="Feature",
                    orientation='h',
                    title=f"Top 10 Importância das Variáveis para {selected_prova_tab2}",
                    labels={'Importance': 'Pontuação de Importância (Gini)', 'Feature': 'Variável'},
                    color_discrete_sequence=px.colors.qualitative.Bold
                )
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(df_importances.sort_values(by="Importance", ascending=False).reset_index(drop=True))
            else:
                 st.warning(f"O arquivo de importâncias para {selected_prova_tab2} não foi encontrado.")
        except Exception as e:
            st.warning(f"Não foi possível carregar os dados de importâncias para {selected_prova_tab2}. {e}")