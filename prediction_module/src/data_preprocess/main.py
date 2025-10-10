from database.operations import load_data, update_treineiros, saveData_BD
from data_preprocess.preprocess import preprocess_arvoreDecisao

def main():
    # Select dados 
    df = load_data()

    # Pré-processar
    df_processado, _ = preprocess_arvoreDecisao(df)

    # Save DataBase
    saveData_BD(df_processado, 'dados_enem_consolidado')

    # Metodo Muda diretamente no Banco (O mesmo realizado no README da PRIMEIRA ENTREGA)
    update_treineiros(ano=2014)

    print("Dados processados com sucesso!")
    print(df_processado.head(30))
    print(df_processado.describe())
   

if __name__ == "__main__":
    main()