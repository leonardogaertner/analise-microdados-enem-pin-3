import os
import streamlit as st
import pandas as pd
from sqlalchemy import text

from Dashboards.utils.json_utils import carregar_geojson_local

@st.cache_data(show_spinner="Carregando dados...")
def carregar_dados_db(_engine):
    geojson_data = carregar_geojson_local(os.getenv('LOCAL_GEOJSON_FILENAME'))
    if geojson_data is None:
        st.warning("Não foi possível carregar os dados geográficos para o mapa.")

    try:
        tabela = os.getenv('NOME_TABELA')
        with _engine.connect() as connection:

            query_anos = text(f'SELECT DISTINCT "NU_ANO" FROM "{tabela}" ORDER BY "NU_ANO" DESC')
            query_faixa = text(f'SELECT DISTINCT "TP_FAIXA_ETARIA" FROM "{tabela}" ORDER BY "TP_FAIXA_ETARIA"')
            query_conclusao = text(f'SELECT DISTINCT "TP_ST_CONCLUSAO" FROM "{tabela}" ORDER BY "TP_ST_CONCLUSAO"')

            anos_disponiveis = [str(a[0]) for a in connection.execute(query_anos).fetchall() if a[0] is not None]
            faixas_disponiveis = [f[0] for f in connection.execute(query_faixa).fetchall() if f[0] is not None]
            conclusoes_disponiveis = [c[0] for c in connection.execute(query_conclusao).fetchall() if c[0] is not None]

            colunas_necessarias = [
                "NU_INSCRICAO", "NU_ANO", "TP_FAIXA_ETARIA", "TP_SEXO", "TP_ST_CONCLUSAO",
                "SG_UF_PROVA", "NO_MUNICIPIO_PROVA", 
                "TP_LINGUA", "NU_NOTA_CN", "NU_NOTA_CH", "NU_NOTA_LC",
                "NU_NOTA_MT", "NU_NOTA_REDACAO", "MEDIA_GERAL", "INDICADOR_ABSENTEISMO",
                "TP_COR_RACA", "IN_TREINEIRO"
            ]
            
            colunas_necessarias = sorted(list(set(colunas_necessarias)))
            colunas_query = ", ".join([f'"{col}"' for col in colunas_necessarias])

            colunas_socioeconomicas = f'''
                , "Q006" AS "Q_RENDA"
                , "Q001" AS "Q_ESCOLARIDADE_PAI"
                , "Q002" AS "Q_ESCOLARIDADE_MAE"
            '''
            
            query_total = text(f'SELECT {colunas_query} {colunas_socioeconomicas} FROM "{tabela}"')

            df = pd.read_sql(query_total, connection)

            if 'NU_ANO' in df.columns:
                df['NU_ANO'] = pd.to_numeric(df['NU_ANO'], errors='coerce').astype('Int64')
            if 'TP_SEXO' in df.columns:
                df['TP_SEXO'] = df['TP_SEXO'].astype(str)
            if 'TP_FAIXA_ETARIA' in df.columns:
                df['TP_FAIXA_ETARIA'] = pd.to_numeric(df['TP_FAIXA_ETARIA'], errors='coerce').astype('Int64')
            if 'TP_ST_CONCLUSAO' in df.columns:
                df['TP_ST_CONCLUSAO'] = pd.to_numeric(df['TP_ST_CONCLUSAO'], errors='coerce').astype('Int64')
            if 'TP_LINGUA' in df.columns:
                 df['TP_LINGUA'] = pd.to_numeric(df['TP_LINGUA'], errors='coerce').astype('Int64')
            if 'TP_COR_RACA' in df.columns:
                 df['TP_COR_RACA'] = pd.to_numeric(df['TP_COR_RACA'], errors='coerce').astype('Int64')
            if 'IN_TREINEIRO' in df.columns:
                 df['IN_TREINEIRO'] = pd.to_numeric(df['IN_TREINEIRO'], errors='coerce').astype('Int64')
            
            if 'Q_RENDA' in df.columns:
                 df['Q_RENDA'] = df['Q_RENDA'].astype(str)
            if 'Q_ESCOLARIDADE_PAI' in df.columns:
                 df['Q_ESCOLARIDADE_PAI'] = df['Q_ESCOLARIDADE_PAI'].astype(str)
            if 'Q_ESCOLARIDADE_MAE' in df.columns:
                 df['Q_ESCOLARIDADE_MAE'] = df['Q_ESCOLARIDADE_MAE'].astype(str)

            for col_nota in ['NU_NOTA_CN', 'NU_NOTA_CH', 'NU_NOTA_LC', 'NU_NOTA_MT', 'NU_NOTA_REDACAO', 'MEDIA_GERAL']:
                 if col_nota in df.columns:
                       df[col_nota] = pd.to_numeric(df[col_nota], errors='coerce')

            if 'NO_MUNICIPIO_PROVA' in df.columns:
                df['NO_MUNICIPIO_PROVA'] = df['NO_MUNICIPIO_PROVA'].astype(str).str.strip()

            return df, anos_disponiveis, faixas_disponiveis, conclusoes_disponiveis, geojson_data

    except Exception as e:
        st.error(f"Erro ao conectar ou carregar dados do PostgreSQL: {e}")

        return pd.DataFrame(), [], [], [], geojson_data


@st.cache_data(show_spinner="Buscando municípios...")
def buscar_municipios_por_estado(estado_sigla, _engine):
    if not estado_sigla or estado_sigla == "Todos":
        return []

    try:
        tabela = os.getenv('NOME_TABELA')
        with _engine.connect() as connection:
            query = text(f'''
                SELECT DISTINCT "NO_MUNICIPIO_PROVA"
                FROM "{tabela}"
                WHERE "SG_UF_PROVA" = :estado
                ORDER BY "NO_MUNICIPIO_PROVA" ASC
            ''')
            result = connection.execute(query, {"estado": estado_sigla})
            municipios = [row[0] for row in result.fetchall() if row[0]]
            return sorted(list(set(municipios)))
    except Exception as e:
        st.error(f"Erro ao buscar municípios para {estado_sigla}: {e}")
        return []