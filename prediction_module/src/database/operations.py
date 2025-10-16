import pandas as pd
from sqlalchemy import text

from database.connection import engine

def load_data():
    tabela = "dados_enem_consolidado"
    query = f"SELECT * FROM {tabela}"
    df = pd.read_sql(query, engine)
    return df

def saveData_BD(df, nomeTabela:str):
    df.to_sql(nomeTabela, engine, if_exists='replace', index=False)
    print(f"{len(df)} registros salvos na tabela '{nomeTabela}'")

# Substitui a necessidade de rodar os SQL do README.MD ==> DIRETO NO BANCO 
def update_treineiros(ano=2014):
    update_query = text(f"""
        UPDATE public.dados_enem_consolidado
        SET "IN_TREINEIRO" = CASE
            WHEN "TP_ST_CONCLUSAO" = 3 AND "TP_FAIXA_ETARIA" <= 2 THEN 1
            ELSE 0
        END
        WHERE "NU_ANO" = {ano};
    """)

    select_query = text(f"""
        SELECT
            "IN_TREINEIRO",
            COUNT(*) AS total_registros
        FROM
            public.dados_enem_consolidado
        WHERE
            "NU_ANO" = {ano}
        GROUP BY
            "IN_TREINEIRO";
    """)

    with engine.begin() as conn:
        print(f"\nAtualizando IN_TREINEIRO para o ano {ano}...")
        conn.execute(update_query)
        print("Atualização concluída")

        print("Verificando resultados...")
        result = conn.execute(select_query)
        df_result = pd.DataFrame(result.fetchall(), columns=result.keys())

    print("\nResumo da atualização:")
    print(df_result)

    return df_result


