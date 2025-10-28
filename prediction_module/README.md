# Módulo de Predição de Desempenho no ENEM (Módulo 3)

Este módulo tem como objetivo facilitar a análise do desempenho dos estudantes no ENEM utilizando **modelos preditivos**, especificamente **árvores de decisão**. Ele inclui funcionalidades para pré-processamento dos dados e treinamento de modelos, permitindo mapear variáveis socioeconômicas e respostas do exame às notas obtidas pelos candidatos.

---

## Funcionalidades

1. **Pré-processamento de Dados (`preprocess.py`)**  
   - Remoção de colunas irrelevantes (`NU_INSCRICAO`, `TP_PRESENCA_*`, `TP_STATUS_REDACAO`, `TP_ST_REDACAO`, codigos, gabaritos, respostas)  
   - Tratamento de valores faltantes:
     - Notas: substituição de `NaN` por `-1` ou categorização (`ruim`, `regular`, `bom`, `ótimo`) para notas
   - Codificação de variáveis categóricas usando `LabelEncoder`  

2. **Manipulação do Banco de Dados (`operations.py`)**  
   - Carregamento completo da tabela `dados_enem_consolidado`  
   - Salvamento de DataFrames processados no banco  


3. **Treinamento do Modelo (`train_model.py`)**  
   - Algoritmo utilizado: `DecisionTreeClassifier`
   - Split treino/teste com `train_test_split` e `stratify=y` para classificação  
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
    python -m data_preprocess.main
```

2. **Treinar Modelo**  
- Treinando referente a váriavel: `target_col = "NU_NOTA_CH"` em (`train_model.py`)

```bash
    python -m models.train_model
```







