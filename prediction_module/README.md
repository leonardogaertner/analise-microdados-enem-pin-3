# Módulo de Predição de Desempenho no ENEM (Módulo 3)

Este módulo tem como objetivo facilitar a análise do desempenho dos estudantes no ENEM utilizando **modelos preditivos**, especificamente **árvores de decisão**. Ele inclui funcionalidades para pré-processamento dos dados e treinamento de modelos, permitindo mapear variáveis socioeconômicas e respostas do exame às notas obtidas pelos candidatos.

---

### 1. Pré-processamento de Dados (`data_preprocess/preprocess.py`)
Responsável por preparar os microdados do ENEM para uso em modelos preditivos.  

#### Principais Etapas:
- **Remoção de colunas irrelevantes**, como:
  - Identificadores (`NU_INSCRICAO`, `CO_PROVA_*`, `CO_MUNICIPIO_*`)
  - Presenças e status (`TP_PRESENCA_*`, `TP_STATUS_REDACAO`, `TP_ST_CONCLUSAO`)
  - Gabaritos e respostas (`TX_GABARITO_*`, `TX_RESPOSTAS_*`)
- **Tratamento de valores faltantes**:
  - Notas: substituição de `-1` por `NaN`
  - Variáveis categóricas: preenchimento com `"ND"`
- **Categorização das notas** com base nos percentis **15** e **85**:
  - `0` → baixo desempenho  (abaixo de 15º percentil)
  - `1` → médio desempenho  (entre 15º-85º percentil)
  - `2` → alto desempenho  (acima de 85º percentil)
  - `-1` → dados ausente
- **Codificação de variáveis categóricas** com `LabelEncoder`
- Substituição final de valores ausentes por `-1` para compatibilidade com o scikit-learn

---

### 2. Manipulação do Banco de Dados (`database/operations.py`)

Gerencia o carregamento e salvamento de dados diretamente no PostgreSQL.

#### Funcionalidades:
- **`load_data()`** — Carrega a tabela `dados_enem_consolidado`
- **`saveData_BD(df, nomeTabela)`** — Salva um `DataFrame` processado em uma nova tabela


3. **Treinamento do Modelo (`train_model.py`)**

   - Algoritmo utilizado: `Random Forest`
   - Otimização de hiperparâmetros 
   - Busca aleatória dos hiperparâmetros via `RandomizedSearchCV`
     - `n_estimators`: Número de árvores na floresta.
     - `max_depth`: Profundidade máxima permitida para cada árvore.
     - `min_samples_split`: Número mínimo de amostras necessárias para dividir um nó interno
     - `min_samples_leaf`: Número mínimo de amostras exigidas em um nó folha.

   - Balanceamento de classe com o `SMOTE`
   - Avaliação de desempenho com:
     - Accuracy
     - Classification report (precision, recall, F1-score)
     - Análise da importância das features 
   

# Pré-requisitos
- Python 3.11+
- Pacotes do Python: 

```bash
pip install pandas numpy scikit-learn sqlalchemy psycopg2-binary
```

# Conexão com Banco (.env)
- Altere os `DB_USER` e `DB_PASS`

```bash
    DB_USER=usuario
    DB_PASS=senha
    DB_HOST=localhost
    DB_PORT=5432
    DB_NAME=microdados
```

# SCRIPTs
- Acessar a pasta: 
```bash
    cd prediction_module/src
```

1. **Pré-processamento para Módulo de Predição**  

```bash
    python -m data_preprocess.preprocess
```

2. **Treinar Modelo**  
- Treinando referente a váriavel: `target_col = "NU_NOTA_CH"` em (`train_model.py`)

```bash
    python -m models.train_model
```







