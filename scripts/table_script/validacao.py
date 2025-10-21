# -*- coding: utf-8 -*-

import pandas as pd
from sqlalchemy import create_engine, text, types
import time
import glob
from io import StringIO
import numpy as np
import os

# --- Configuração do Banco de Dados PostgreSQL (deve ser idêntica ao script principal) ---
DB_USER = 'postgres'
DB_PASS = 'aluno'
DB_HOST = 'localhost'
DB_NAME = 'microdados'
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"

# --- Configurações dos Campos e Arquivos (deve ser idêntica ao script principal) ---
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

def aplicar_regras_de_negocio(df_chunk):
    """
    CÓPIA EXATA da função do script principal para garantir consistência.
    """
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
            df_chunk.loc[condicao_2014, 'Q007'] = None
    return df_chunk

# --- Início da Verificação ---
start_time = time.time()
print("--- Iniciando Script de Verificação de Dados ---")

try:
    # --- FASE 1: Reconstruir os Dados de Origem ---
    print("\nFASE 1: Lendo e transformando arquivos CSV de origem...")
    # (código da fase 1 omitido para brevidade, continua o mesmo)
    lista_arquivos_csv = sorted(glob.glob('*.csv'))
    master_columns = set()
    for nome_arquivo in lista_arquivos_csv:
        if 'teste.py' in nome_arquivo or 'script.py' in nome_arquivo: continue
        df_header = pd.read_csv(nome_arquivo, sep=';', encoding='latin-1', nrows=1)
        if 'NU_SEQUENCIAL' in df_header.columns:
            df_header.rename(columns={'NU_SEQUENCIAL': 'NU_INSCRICAO'}, inplace=True)
        colunas_filtradas = {col for col in df_header.columns if col in campos_desejados}
        master_columns.update(colunas_filtradas)
    master_columns_list = sorted(list(master_columns))
    colunas_para_inteiro = [c for c in master_columns_list if c.startswith(('CO_', 'TP_', 'NU_ANO', 'IN_')) and not c.startswith('Q') and c != 'TP_SEXO']
    lista_dfs_origem = []
    for nome_arquivo in lista_arquivos_csv:
        if 'RESULTADOS_2024' in nome_arquivo or 'teste.py' in nome_arquivo or 'script.py' in nome_arquivo:
            continue
        print(f"- Processando arquivo: {nome_arquivo}")
        df = pd.read_csv(nome_arquivo, sep=';', encoding='latin-1', low_memory=False)
        if 'NU_SEQUENCIAL' in df.columns:
            df.rename(columns={'NU_SEQUENCIAL': 'NU_INSCRICAO'}, inplace=True)
        for col in df.columns:
            if col.startswith('Q'):
                df[col] = df[col].astype(str).replace('nan', None)
        for col in colunas_para_inteiro:
            if col in df.columns:
                cleaned_col = df[col].astype(str).str.strip()
                df[col] = pd.to_numeric(cleaned_col, errors='coerce').astype('Int64')
        df = aplicar_regras_de_negocio(df)
        lista_dfs_origem.append(df)
    df_origem = pd.concat(lista_dfs_origem, ignore_index=True)
    df_origem = df_origem.reindex(columns=master_columns_list)
    print("Dados de origem reconstruídos com sucesso.")

    # --- FASE 2: Carregar os Dados do Banco ---
    print("\nFASE 2: Lendo dados da tabela no PostgreSQL...")
    engine = create_engine(DATABASE_URL)
    with engine.connect() as connection:
        df_banco = pd.read_sql_table(nome_tabela, connection)
    print("Dados do banco carregados com sucesso.")
    
    # --- FASE 3: Preparar para Comparação ---
    print("\nFASE 3: Alinhando, ordenando e normalizando dados para comparação...")
    df_banco = df_banco[master_columns_list]
    df_origem.sort_values(by='NU_INSCRICAO', inplace=True)
    df_banco.sort_values(by='NU_INSCRICAO', inplace=True)
    df_origem.reset_index(drop=True, inplace=True)
    df_banco.reset_index(drop=True, inplace=True)
    
    # --- CORREÇÃO FINAL: Normalização Definitiva ---
    # Cria cópias para evitar avisos
    df_origem_norm = df_origem.copy()
    df_banco_norm = df_banco.copy()

    for col in master_columns_list:
        # Converte tudo para string para iniciar
        df_origem_norm[col] = df_origem_norm[col].astype(str)
        df_banco_norm[col] = df_banco_norm[col].astype(str)
        
        # Substitui todas as representações de nulo por um padrão (string vazia)
        df_origem_norm[col] = df_origem_norm[col].replace({'<NA>': '', 'nan': '', 'None': ''})
        df_banco_norm[col] = df_banco_norm[col].replace({'<NA>': '', 'nan': '', 'None': ''})
        
        # Remove o '.0' do final dos números que eram floats
        df_origem_norm[col] = df_origem_norm[col].str.replace(r'\.0$', '', regex=True)
        df_banco_norm[col] = df_banco_norm[col].str.replace(r'\.0$', '', regex=True)
            
    print("Dados prontos para a comparação.")

    # --- FASE 4: Comparar e Gerar Relatório ---
    print("\nFASE 4: Comparando os dados normalizados...")
    
    if df_origem_norm.equals(df_banco_norm):
        print("\n--- VERIFICAÇÃO CONCLUÍDA COM SUCESSO ---")
        print("SUCESSO: Os dados nos arquivos de origem (após transformação) e no banco de dados são 100% idênticos.")
    else:
        print("\n--- VERIFICAÇÃO FALHOU ---")
        print("ERRO: Os dados não são idênticos.")
        diferencas = df_origem_norm.compare(df_banco_norm).rename(columns={'self': 'ORIGEM_CSV', 'other': 'BANCO_DADOS'})
        print("Amostra das primeiras 10 linhas com valores diferentes:")
        print(diferencas.head(10))

except Exception as e:
    print(f"\nOcorreu um erro durante a verificação: {e}")
finally:
    end_time = time.time()
    total_time = end_time - start_time
    print(f"\n--- Verificação concluída em {total_time:.2f} segundos ---")