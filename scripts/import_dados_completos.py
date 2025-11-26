# -*- coding: utf-8 -*-

import pandas as pd
from sqlalchemy import create_engine, text, types
import time

# --- Configuração do Banco de Dados PostgreSQL ---
DB_USER = 'postgres'
DB_PASS = 'aluno'  # CORRIGIDO: mesma senha do primeiro script
DB_HOST = 'localhost'
DB_NAME = 'microdados'
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}/{DB_NAME}"

# --- Configurações ---
ARQUIVO_CSV = 'dados_completo.csv'
NOME_TABELA = 'questoes_enem'
TAMANHO_CHUNK = 50000

# --- Início da operação ---
start_time = time.time()
print(f"Iniciando a operação às {time.ctime()}...")

try:
    # FASE 1: Analisando estrutura do CSV
    print("\n--- FASE 1: Analisando estrutura do CSV... ---")
    df_header = pd.read_csv(ARQUIVO_CSV, encoding='utf-8-sig', nrows=5)
    print(f"Colunas encontradas: {list(df_header.columns)}")
    print(f"\nPrimeiras linhas:")
    print(df_header.head())

    # Mapeamento de colunas do CSV para nomes padronizados do banco
    rename_columns = {
        'Ano': 'ano',
        'Cor': 'cor',
        'Nº Questão': 'numero_questao',
        'Gabarito': 'gabarito',
        'Sigla da Área': 'sigla_area',
        'Área': 'area',
        'Língua': 'lingua',
        'Habilidade': 'habilidade',
        'Item Abandonado': 'item_abandonado',
        'Motivo Abandono': 'motivo_abandono',
        'Item Adaptado': 'item_adaptado',
        'Parâmetro A': 'parametro_a',
        'Parâmetro B': 'parametro_b',
        'Parâmetro C': 'parametro_c',
        'Itens': 'itens',
        'Provas': 'provas',
        'Versão Digital': 'versao_digital'
    }

    # Definindo tipos de dados para o SQL
    tipos_de_dados_sql = {
        'ano': types.INTEGER,
        'cor': types.TEXT,
        'numero_questao': types.INTEGER,
        'gabarito': types.TEXT,
        'sigla_area': types.TEXT,
        'area': types.TEXT,
        'lingua': types.TEXT,
        'habilidade': types.TEXT,
        'item_abandonado': types.INTEGER,
        'motivo_abandono': types.TEXT,
        'item_adaptado': types.TEXT,
        'parametro_a': types.FLOAT,
        'parametro_b': types.FLOAT,
        'parametro_c': types.FLOAT,
        'itens': types.INTEGER,
        'provas': types.TEXT,
        'versao_digital': types.TEXT
    }

    # FASE 2: Criando tabela e carregando dados
    print("\n--- FASE 2: Criando tabela e carregando dados... ---")
    engine = create_engine(DATABASE_URL)

    # Removendo tabela antiga se existir
    with engine.connect() as connection:
        connection.execute(text(f"DROP TABLE IF EXISTS {NOME_TABELA};"))
        connection.commit()
        print(f"Tabela '{NOME_TABELA}' antiga removida (se existia).")

    # Processando o CSV em chunks
    csv_iterator = pd.read_csv(
        ARQUIVO_CSV,
        encoding='utf-8-sig',
        low_memory=False,
        chunksize=TAMANHO_CHUNK
    )

    is_first_chunk = True
    total_registros = 0
    chunk_num = 0

    for chunk in csv_iterator:
        chunk_num += 1

        # Renomear colunas para padrão do banco de dados
        chunk = chunk.rename(columns=rename_columns)

        # Limpeza de dados
        # Remover espaços em branco das colunas de texto
        for col in chunk.select_dtypes(include=['object']).columns:
            if col not in ['parametro_a', 'parametro_b', 'parametro_c']:
                chunk[col] = chunk[col].astype(str).str.strip()
                chunk[col] = chunk[col].replace('nan', None)

        # Converter colunas numéricas
        for col in ['ano', 'numero_questao', 'item_abandonado', 'itens']:
            if col in chunk.columns:
                chunk[col] = pd.to_numeric(chunk[col], errors='coerce').astype('Int64')

        for col in ['parametro_a', 'parametro_b', 'parametro_c']:
            if col in chunk.columns:
                chunk[col] = pd.to_numeric(chunk[col], errors='coerce')

        # Enviando para o banco
        if is_first_chunk:
            print(f"  Chunk {chunk_num}: Criando tabela e enviando {len(chunk)} linhas...", end="", flush=True)
            chunk.to_sql(NOME_TABELA, engine, if_exists='replace', index=False, dtype=tipos_de_dados_sql)
            is_first_chunk = False
        else:
            print(f"  Chunk {chunk_num}: Enviando {len(chunk)} linhas...", end="", flush=True)
            chunk.to_sql(NOME_TABELA, engine, if_exists='append', index=False, dtype=tipos_de_dados_sql)

        total_registros += len(chunk)
        print(" OK.")

    print(f"\nTotal de {total_registros} registros carregados na tabela '{NOME_TABELA}'.")

    # FASE 3: Padronização dos nomes das áreas
    print("\n--- FASE 3: Padronizando nomes das áreas... ---")
    with engine.connect() as connection:
        # Atualizar área baseado na sigla
        update_cn = text(f"UPDATE {NOME_TABELA} SET area = 'Ciências da Natureza e suas Tecnologias' WHERE sigla_area = 'CN';")
        result_cn = connection.execute(update_cn)
        connection.commit()
        print(f"  ✓ Ciências da Natureza: {result_cn.rowcount} registros atualizados")

        update_ch = text(f"UPDATE {NOME_TABELA} SET area = 'Ciências Humanas e suas Tecnologias' WHERE sigla_area = 'CH';")
        result_ch = connection.execute(update_ch)
        connection.commit()
        print(f"  ✓ Ciências Humanas: {result_ch.rowcount} registros atualizados")

        update_mt = text(f"UPDATE {NOME_TABELA} SET area = 'Matemática e suas Tecnologias' WHERE sigla_area = 'MT';")
        result_mt = connection.execute(update_mt)
        connection.commit()
        print(f"  ✓ Matemática: {result_mt.rowcount} registros atualizados")

        update_lc = text(f"UPDATE {NOME_TABELA} SET area = 'Linguagens, Códigos e suas Tecnologias' WHERE sigla_area = 'LC';")
        result_lc = connection.execute(update_lc)
        connection.commit()
        print(f"  ✓ Linguagens e Códigos: {result_lc.rowcount} registros atualizados")

    # FASE 4: Verificando dados carregados no banco
    print("\n--- FASE 4: Verificando dados carregados no banco... ---")
    with engine.connect() as connection:
        # Contagem por ano
        query_ano = text(f'SELECT ano, COUNT(*) as total_registros FROM {NOME_TABELA} GROUP BY ano ORDER BY ano;')
        df_ano = pd.read_sql_query(query_ano, connection)
        print("\nContagem de registros por ano:")
        print(df_ano.to_string(index=False))

        # Contagem por área
        query_area = text(f'SELECT area, COUNT(*) as total_registros FROM {NOME_TABELA} GROUP BY area ORDER BY area;')
        df_area = pd.read_sql_query(query_area, connection)
        print("\nContagem de registros por área:")
        print(df_area.to_string(index=False))

        # Total geral
        query_total = text(f'SELECT COUNT(*) as total FROM {NOME_TABELA};')
        df_total = pd.read_sql_query(query_total, connection)
        print(f"\nTotal geral de registros: {df_total['total'].iloc[0]}")

except Exception as e:
    print(f"\nOcorreu um erro inesperado: {e}")
    import traceback
    traceback.print_exc()
finally:
    end_time = time.time()
    total_time = end_time - start_time
    print(f"\n--- Operação concluída em {total_time:.2f} segundos ---")
