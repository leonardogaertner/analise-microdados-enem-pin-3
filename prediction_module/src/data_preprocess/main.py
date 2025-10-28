from database.operations import load_data, saveData_BD
from data_preprocess.preprocess import preprocess_data

if __name__ == "__main__":
    # Select dados 
    df = load_data()

    # Pré-processar
    df_processado, _ = preprocess_data(df)

    # Save DataBase
    saveData_BD(df_processado, 'dados_enem_consolidado')

    print("Dados processados com sucesso!")
    print(df_processado.head(30))
    print(df_processado.describe())
   