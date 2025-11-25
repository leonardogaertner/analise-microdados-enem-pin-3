# -*- coding: utf-8 -*-

import pandas as pd
from sqlalchemy import create_engine, text, types
import time
import glob
from io import StringIO
import numpy as np
import os

# --- Configuração do Banco de Dados PostgreSQL ---
DB_USER = 'postgres'
DB_PASS = 'aluno'
DB_HOST = 'localhost'
DB_NAME = 'microdados'
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"

# --- Configurações dos Campos e Arquivos ---
campos_str = (
    "NU_INSCRICAO;NU_ANO;TP_FAIXA_ETARIA;TP_SEXO;TP_ESTADO_CIVIL;TP_COR_RACA;"
    "TP_NACIONALIDADE;TP_ST_CONCLUSAO;TP_ANO_CONCLUIU;TP_ESCOLA;TP_ENSINO;"
    "IN_TREINEIRO;CO_MUNICIPIO_ESC;NO_MUNICIPIO_ESC;CO_UF_ESC;SG_UF_ESC;"
    "TP_DEPENDENCIA_ADM_ESC;TP_LOCALIZACAO_ESC;TP_SIT_FUNC_ESC;CO_MUNICIPIO_PROVA;"
    "NO_MUNICIPIO_PROVA;CO_UF_PROVA;SG_UF_PROVA;TP_PRESENCA_CN;TP_PRESENCA_CH;"
    "TP_PRESENCA_LC;TP_PRESENCA_MT;CO_PROVA_CN;CO_PROVA_CH;CO_PROVA_LC;CO_PROVA_MT;"
    "NU_NOTA_CN;NU_NOTA_CH;NU_NOTA_LC;NU_NOTA_MT;TX_RESPOSTAS_CN;TX_RESPOSTAS_CH;"
    "TX_RESPOSTAS_LC;TX_RESPOSTAS_MT;TP_LINGUA;TX_GABARITO_CN;TX_GABARITO_CH;"
    "TX_GABARITO_LC;TX_GABARITO_MT;TP_STATUS_REDACAO;NU_NOTA_COMP1;NU_NOTA_COMP2;"
    "NU_NOTA_COMP3;NU_NOTA_COMP4;NU_NOTA_COMP5;NU_NOTA_REDACAO;Q001;Q002;Q003;"
    "Q004;Q005;Q006;Q007;Q008;Q009;Q010;Q011;Q012;Q013;Q014;Q015;Q016;Q017;"
    "Q018;Q019;Q020;Q021;Q022;Q023;Q024;Q025"
)
campos_desejados = set(campos_str.split(';'))
nome_tabela = 'dados_enem_consolidado'
TAMANHO_CHUNK = 50000

def upload_com_progresso(df_chunk, conn, nome_tabela):
    buffer = StringIO()
    df_chunk.to_csv(buffer, index=False, header=False, sep=';')
    buffer.seek(0)
    cursor = conn.cursor()
    try:
        sql_copy = f"COPY {nome_tabela} FROM STDIN WITH (FORMAT CSV, DELIMITER ';')"
        cursor.copy_expert(sql=sql_copy, file=buffer)
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()

def aplicar_regras_de_negocio(df_chunk):
    # (função aplicar_regras_de_negocio omitida para brevidade, continua a mesma)
    colunas_necessarias_2024 = ['Q006', 'Q007', 'Q021', 'Q024']
    if 'NU_ANO' in df_chunk.columns and all(c in df_chunk.columns for c in colunas_necessarias_2024):
        condicao_2024 = df_chunk['NU_ANO'] == 2024
        if not df_chunk.loc[condicao_2024].empty:
            df_chunk.loc[condicao_2024, 'Q006'] = df_chunk.loc[condicao_2024, 'Q007']
            df_chunk.loc[condicao_2024, 'Q024'] = df_chunk.loc[condicao_2024, 'Q021']
            df_chunk.loc[condicao_2024, 'Q007'] = None
            df_chunk.loc[condicao_2024, 'Q021'] = None
    colunas_necessarias_2014 = [
        'Q003', 'Q004', 'Q005', 'Q006', 'Q010', 'Q015', 'Q016', 'Q017', 'Q020',
        'Q007', 'Q022', 'Q023', 'Q024', 'Q025'
    ]
    if 'NU_ANO' in df_chunk.columns and all(c in df_chunk.columns for c in colunas_necessarias_2014):
        condicao_2014 = df_chunk['NU_ANO'] == 2014
        if not df_chunk.loc[condicao_2014].empty:
            df_chunk.loc[condicao_2014, 'Q005'] = df_chunk.loc[condicao_2014, 'Q004']
            df_chunk.loc[condicao_2014, 'Q006'] = df_chunk.loc[condicao_2014, 'Q003']
            mapeamento_2014 = {'A': 'B', 'B': 'C', 'C': None, 'D': 'A'}
            df_chunk.loc[condicao_2014, 'Q024'] = df_chunk.loc[condicao_2014, 'Q010'].map(mapeamento_2014)
            df_chunk.loc[condicao_2014, 'Q023'] = df_chunk.loc[condicao_2014, 'Q015'].map(mapeamento_2014)
            df_chunk.loc[condicao_2014, 'Q022'] = df_chunk.loc[condicao_2014, 'Q016'].map(mapeamento_2014)
            df_chunk.loc[condicao_2014, 'Q025'] = df_chunk.loc[condicao_2014, 'Q017'].map(mapeamento_2014)
            colunas_para_anular = ['Q003', 'Q004', 'Q007', 'Q010', 'Q015', 'Q016', 'Q017']
            for col in colunas_para_anular:
                df_chunk.loc[condicao_2014, col] = None
    return df_chunk

# --- Início da operação ---
start_time = time.time()
print(f"Iniciando a operação às {time.ctime()}...")

try:
    # FASE 1: Analisando cabeçalhos...
    print("\n--- FASE 1: Analisando cabeçalhos... ---")
    lista_arquivos_csv = sorted(glob.glob('*.csv'))
    master_columns = set()
    for nome_arquivo in lista_arquivos_csv:
        if 'script.py' in nome_arquivo or 'teste.py' in nome_arquivo: continue
        df_header = pd.read_csv(nome_arquivo, sep=';', encoding='latin-1', nrows=1)
        if 'NU_SEQUENCIAL' in df_header.columns:
            df_header.rename(columns={'NU_SEQUENCIAL': 'NU_INSCRICAO'}, inplace=True)
        colunas_filtradas = {col for col in df_header.columns if col in campos_desejados}
        master_columns.update(colunas_filtradas)
    master_columns_list = sorted(list(master_columns))
    print(f"Análise concluída. {len(master_columns_list)} colunas únicas serão usadas.")
    
    colunas_para_inteiro = [c for c in master_columns_list if c.startswith(('CO_','TP_','NU_ANO','IN_')) and not c.startswith('Q') and c != 'TP_SEXO']
    tipos_de_dados_sql = {c: types.TEXT for c in master_columns_list if c.startswith(('Q', 'TX_')) or c == 'TP_SEXO'}
    tipos_de_dados_sql.update({c: types.FLOAT for c in master_columns_list if c.startswith('NU_NOTA')})

    # FASE 2: Processando e carregando dados...
    print("\n--- FASE 2: Processando e carregando dados... ---")
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        connection.execute(text(f"DROP TABLE IF EXISTS {nome_tabela};"))
        connection.commit()
        print(f"Tabela '{nome_tabela}' antiga removida (se existia).")

    is_first_chunk = True
    for nome_arquivo in lista_arquivos_csv:
        if 'RESULTADOS_2024' in nome_arquivo or 'script.py' in nome_arquivo or 'teste.py' in nome_arquivo:
            print(f"\nIgnorando arquivo: {nome_arquivo}")
            continue

        print(f"\nProcessando arquivo: {nome_arquivo}")
        csv_iterator = pd.read_csv(nome_arquivo, sep=';', encoding='latin-1', low_memory=False, chunksize=TAMANHO_CHUNK)
        
        chunk_num = 0
        for chunk in csv_iterator:
            chunk_num += 1
            if 'NU_SEQUENCIAL' in chunk.columns:
                chunk.rename(columns={'NU_SEQUENCIAL': 'NU_INSCRICAO'}, inplace=True)

            # --- ORDEM DE OPERAÇÕES CORRIGIDA ---
            # 1. Alinha as colunas PRIMEIRO, adicionando as que faltam como NULO
            chunk_alinhado = chunk.reindex(columns=master_columns_list)

            # 2. Agora, aplica a limpeza de tipos
            for col in chunk_alinhado.columns:
                if col.startswith('Q'):
                    chunk_alinhado[col] = chunk_alinhado[col].astype(str).replace('nan', None)
            for col in colunas_para_inteiro:
                if col in chunk_alinhado.columns:
                    cleaned_col = chunk_alinhado[col].astype(str).str.strip()
                    numeric_col = pd.to_numeric(cleaned_col, errors='coerce')
                    chunk_alinhado[col] = numeric_col.astype('Int64')
            
            # 3. Finalmente, aplica as regras de negócio ao chunk já alinhado e limpo
            chunk_processado = aplicar_regras_de_negocio(chunk_alinhado)
            
            # 4. Envia para o banco
            if is_first_chunk:
                print(f"  Chunk {chunk_num}: Criando tabela e enviando {len(chunk_processado)} linhas...", end="", flush=True)
                chunk_processado.to_sql(nome_tabela, engine, if_exists='replace', index=False, dtype=tipos_de_dados_sql)
                is_first_chunk = False
            else:
                print(f"  Chunk {chunk_num}: Enviando {len(chunk_processado)} linhas...", end="", flush=True)
                with engine.raw_connection().driver_connection as conn:
                    upload_com_progresso(chunk_processado, conn, nome_tabela)
            
            print(" OK.")
            
    print(f"\nTodos os arquivos foram processados e carregados na tabela '{nome_tabela}'.")
    
    # FASE 3: Verificando dados carregados no banco...
    print("\n--- FASE 3: Verificando dados carregados no banco... ---")
    with engine.connect() as connection:
        query = text(f'SELECT "NU_ANO", COUNT(*) as total_registros FROM {nome_tabela} GROUP BY "NU_ANO" ORDER BY "NU_ANO";')
        df_verificacao = pd.read_sql_query(query, connection)
        print("Contagem de registros por ano na tabela final:")
        print(df_verificacao.to_string(index=False))

except Exception as e:
    print(f"\nOcorreu um erro inesperado: {e}")
finally:
    end_time = time.time()
    total_time = end_time - start_time
    print(f"\n--- Operação concluída em {total_time:.2f} segundos ---")