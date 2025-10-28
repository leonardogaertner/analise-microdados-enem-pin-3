import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder

def preprocess_arvoreDecisao(df: pd.DataFrame, categorizar_colunas=True):
    df = removerColunas(df) 
    df = tratarDadosFaltantes(df)

    encoders = {}
    if categorizar_colunas:
        df = categorizarNotas(df)
        df, encoders = codificarVariaveisCategoricas(df)
    
    # Preencher NaNs restantes com -1 (para algoritmos que não aceitam NaN)
    df.fillna(-1, inplace=True)
    
    return df, encoders



def removerColunas(df):
    colunas_remover = [
        "NU_INSCRICAO",
        "CO_MUNICIPIO_PROVA", "CO_MUNICIPIO_ESC",
        "TP_NACIONALIDADADE",
        "TX_GABARITO_CH", "TX_GABARITO_CN", "TX_GABARITO_LC", "TX_GABARITO_MT",
        "TX_RESPOSTAS_CH", "TX_RESPOSTAS_CN", "TX_RESPOSTAS_LC", "TX_RESPOSTAS_MT"
    ]
    return df.drop(columns=[c for c in colunas_remover if c in df.columns], errors="ignore")

# Manter as colunas NaN e tratar como ND as categóricas --> Object
def tratarDadosFaltantes(df):
    colunas_notas = ["NU_NOTA_CH","NU_NOTA_CN","NU_NOTA_LC","NU_NOTA_MT","NU_NOTA_REDACAO"]
    for col in colunas_notas:
        if col in df.columns:
            df[col] = df[col].replace(-1, np.nan)  

    # Colunas q comecam com NO_ e categóricas
    no_cols = [c for c in df.columns if c.startswith("NO_") and df[c].dtype == "object"]
    for col in no_cols:
            df[col] = df[col].fillna("ND").astype(str)
    
    # Outras categóricas
    cat_cols = df.select_dtypes(include=['object']).columns.tolist()
    for col in cat_cols:
        if col not in no_cols:
            df[col] = df[col].fillna("ND").astype(str)

    return df

def categorizar_nota(nota):
    
    if pd.isna(nota) or nota < 0:
        return "ND"
    elif nota < 400:
        return "ruim"
    elif nota < 500:
        return "regular"
    elif nota < 700:
        return "bom"
    else:
        return "otimo"

def categorizarNotas(df):
    colunas_notas = ["NU_NOTA_CH", "NU_NOTA_CN", "NU_NOTA_LC", "NU_NOTA_MT", "NU_NOTA_REDACAO"]
    for col in colunas_notas:
        if col in df.columns:
            df[col] = df[col].apply(categorizar_nota)
    return df

def codificarVariaveisCategoricas(df):
    #Transforma variáveis categóricas em números usando LabelEncoder
    encoders = {}
    categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
    for col in categorical_cols:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
        encoders[col] = le
    return df, encoders

  




