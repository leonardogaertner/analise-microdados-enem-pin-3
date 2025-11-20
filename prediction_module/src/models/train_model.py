from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import pandas as pd
from imblearn.over_sampling import SMOTE

from database.operations import load_data

import joblib
import os

#MODELS
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import RandomizedSearchCV

    
def preprocess_data(df, target_col, nota_cols):
     #Filtragem de dados i.e remoção de dados ausentes
    df_filtered = df[df[target_col] != -1].copy()   

    #Ignorar demais notas (modelo não pode treinar com as demais notas) ==> evitar vazamento de informação
    ignore_cols = [col for col in nota_cols if col != target_col]
    print(f"Ignorando colunas: {ignore_cols}")

    #Evitação de vazamento de informação
    X = df_filtered.drop(columns=[target_col] + ignore_cols, errors="ignore")    
    y = df_filtered[target_col]

    X_res, y_res = SMOTE(random_state=42).fit_resample(X, y)
    return X_res, y_res


def train_model(X_train, y_train):
    """"
        Treina o modelo RandomForest com RandomizedSearchCV

        @param X_train: Conjunto de treinamento (features)
        @param y_train: Rótulos de treinamento
        @return: modelo treinado
    """

    #OBS: Se overfitting → aumente min_samples_leaf, min_samples_split ou reduza max_depth.
    param_dist = {
        'n_estimators': [200, 400, 600],
        'max_depth': [10, 12, 15, 18],
        'min_samples_split': [2, 5, 10],
        'min_samples_leaf': [1, 2, 4],
        'max_features': ['sqrt', 'log2']
    }

    model = RandomizedSearchCV(
        RandomForestClassifier(class_weight='balanced', random_state=42, n_jobs=-1),
        param_distributions=param_dist,
        n_iter=20,
        scoring='f1_macro',
        cv=3,
        verbose=2
    )

    #model = DecisionTreeClassifier(max_depth=10, class_weight="balanced",random_state=42)

    #Treinamento
    model.fit(
        X_train, y_train
    )

    return model

def metrics(model, X_test, y_test, X_columns):
    """
        Avaliação das métricas do modelo e apresentação das importância das features
    """
    y_pred = model.predict(X_test)

    print("Accuracy:", accuracy_score(y_test, y_pred))
    print(classification_report(y_test, y_pred, zero_division=0))

    # Importancia das variáveis (Mostra as 30 mais importantes)
    # Use o parâmetro X_columns — não X.columns
    if hasattr(model, "best_estimator_"):
        estimator = model.best_estimator_
    else:
        estimator = model

    importances = pd.Series(estimator.feature_importances_, index=X_columns)
    print(importances.sort_values(ascending=False).head(30))

    # Visualização
    importances.sort_values(ascending=True).tail(15).plot(kind="barh")

def save_model(model, target_col):
    #CAminho
    save_dir = "./saved_model"
    os.makedirs(save_dir, exist_ok=True)

    model_filename = os.path.join(save_dir, f"randomForest_{target_col}.pkl")

    #Salvar
    joblib.dump(model.best_estimator_, model_filename)
    print(f"Modelo salvo com sucesso em: {model_filename}")

# --- NOVA FUNÇÃO: SALVAR IMPORTÂNCIA DAS FEATURES ---
def save_feature_importances(model, X_columns, target_col):
    """
    Extrai a importância das features do modelo treinado e salva em um CSV.
    Funciona tanto se `model` for RandomizedSearchCV quanto um estimator.
    """
    save_dir = "./saved_model"
    os.makedirs(save_dir, exist_ok=True)

    # obtém o estimador final
    if hasattr(model, "best_estimator_"):
        estimator = model.best_estimator_
    else:
        estimator = model

    # checa se o estimador tem feature_importances_
    if not hasattr(estimator, "feature_importances_"):
        print("O estimador não possui atributo 'feature_importances_'; não é um modelo baseado em árvores.")
        return

    importances = pd.Series(estimator.feature_importances_, index=X_columns)
    df_importances = importances.sort_values(ascending=False).reset_index()
    df_importances.columns = ['Feature', 'Importance']

    csv_filename = os.path.join(save_dir, f"feature_importances_{target_col}.csv")
    df_importances.to_csv(csv_filename, index=False)
    print(f"Importâncias salvas com sucesso em: {csv_filename}")


if __name__ == "__main__":
    #Loading Dados
    df = load_data()

    #Coluna de Treinamento
    target_col = "NU_NOTA_REDACAO"
    print(df[target_col].value_counts())

    #Listas de colunas (target_col)
    nota_cols = ["NU_NOTA_CH", "NU_NOTA_MT", "NU_NOTA_CN", "NU_NOTA_LC", "NU_NOTA_REDACAO"]

    #Pré-processamento/Manipulação dos dados
    X, y = preprocess_data(df, target_col, nota_cols)

    #Divisão de 80% treino e 20% teste
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # --- NOVO CAMINHO PARA SALVAR OS DADOS DE TESTE ---
    SAVE_DIR_APP = "./saved_model"
    os.makedirs(SAVE_DIR_APP, exist_ok=True)

    # Salva X_test
    X_test_path = os.path.join(SAVE_DIR_APP, "analyzer_X_test.csv")
    X_test.to_csv(X_test_path, index=False)

    # Salva y_test
    y_test_path = os.path.join(SAVE_DIR_APP, "analyzer_y_test.csv")
    y_test.to_csv(y_test_path, index=False)

    print(f"Arquivos de teste salvos com sucesso em: {SAVE_DIR_APP}")
    # Treinamento
    model = train_model(X_train, y_train)

    # Salva importâncias das features
    save_feature_importances(model, X.columns, target_col)

    # Métricas
    metrics(model, X_test, y_test, X.columns)

    # Salvar Modelo
    save_model(model, target_col)
