import pandas as pd
from sqlalchemy import create_engine, text, types
import unicodedata
# --- Bloco de import do psycopg REMOVIDO ---
# SQLAlchemy cuidará da importação do driver
import time
import glob
from io import StringIO
import numpy as np
import os
import traceback
import re

# --- Adição para a FASE 4 (Leitura de .xls) ---
try:
    import xlrd
except ImportError:
    print("AVISO: A biblioteca 'xlrd' não está instalada. Necessária para ler arquivos .xls (Excel 97-2003).")
    print("Execute: pip install xlrd")
# --- Fim das adições de import ---


# --- Configuração do Banco de Dados PostgreSQL ---
DB_USER = os.environ.get('DB_USER', 'postgres')
DB_PASS = os.environ.get('DB_PASS', 'aluno')
DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
DB_NAME = os.environ.get('DB_NAME', 'microdados')
DATABASE_URL = f"postgresql+psycopg://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"

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
    "NU_NOTA_COMP3;NU_NOTA_COMP4;NU_NOTA_COMP5;NU_NOTA_REDACAO;Q001;Q002;Q003;Q004;"
    "Q005;Q006;Q007;Q008;Q009;Q010;Q011;Q012;Q013;Q014;Q015;Q016;Q017;Q018;Q019;"
    "Q020;Q021;Q022;Q023;Q024;Q025"
)
campos_desejados = campos_str.upper().split(';')

# --- Configurações do Processo de Carga ---
nome_tabela = 'dados_enem_consolidado'
chunk_size = 50000
upload_chunksize = 250 # Mantido baixo para evitar erro de parâmetros

script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
diretorio_csv = script_dir

def normalize_col_name(col):
    if not isinstance(col, str):
        return str(col).upper()
    normalized = ''.join(c for c in unicodedata.normalize('NFD', col) if unicodedata.category(c) != 'Mn')
    return normalized.upper()

def aplicar_regras_de_negocio(df, ano):
    # (Função aplicar_regras_de_negocio permanece a mesma da versão anterior -
    #  já incluía verificações de existência de colunas)
    # Garante que colunas esperadas existam antes de usá-las
    expected_q_cols = [f'Q{i:03}' for i in range(1, 26)]
    expected_nota_cols = ['NU_NOTA_CN', 'NU_NOTA_CH', 'NU_NOTA_LC', 'NU_NOTA_MT', 'NU_NOTA_REDACAO']
    expected_presence_cols = ['TP_PRESENCA_CN', 'TP_PRESENCA_CH', 'TP_PRESENCA_LC', 'TP_PRESENCA_MT']
    expected_misc_cols = ['SG_UF_PROVA', 'SG_UF_ESC', 'NO_MUNICIPIO_PROVA', 'TP_DEPENDENCIA_ADM_ESC',
                          'TP_ANO_CONCLUIU', 'NU_ANO', 'TP_ST_CONCLUSAO', 'TP_FAIXA_ETARIA']

    for col in expected_q_cols + expected_nota_cols + expected_presence_cols + expected_misc_cols:
        if col not in df.columns:
            df[col] = pd.Series(index=df.index, dtype=object)

    if ano == 2024:
        if 'Q007' in df.columns: df['Q006'] = df['Q007']
        if 'Q021' in df.columns: df['Q024'] = df['Q021']
    elif ano == 2014:
        if 'Q004' in df.columns: df['Q005'] = df['Q004']
        mapeamento = {'A': 'B', 'B': 'C', 'C': 'D', 'D': 'E', 'E': 'F', 'F': 'G', 'G': 'H'}
        if 'Q001' in df.columns: df['Q001'] = df['Q001'].map(mapeamento)
        if 'Q002' in df.columns: df['Q002'] = df['Q002'].map(mapeamento)
        df['Q007'] = None

    map_regiao = { 'AC': 'Norte', 'AP': 'Norte', 'AM': 'Norte', 'PA': 'Norte', 'RO': 'Norte', 'RR': 'Norte', 'TO': 'Norte', 'AL': 'Nordeste', 'BA': 'Nordeste', 'CE': 'Nordeste', 'MA': 'Nordeste', 'PB': 'Nordeste', 'PE': 'Nordeste', 'PI': 'Nordeste', 'RN': 'Nordeste', 'SE': 'Nordeste', 'DF': 'Centro-Oeste', 'GO': 'Centro-Oeste', 'MT': 'Centro-Oeste', 'MS': 'Centro-Oeste', 'ES': 'Sudeste', 'MG': 'Sudeste', 'RJ': 'Sudeste', 'SP': 'Sudeste', 'PR': 'Sul', 'RS': 'Sul', 'SC': 'Sul' }
    map_capitais = { 'AC': 'Rio Branco', 'AL': 'Maceió', 'AP': 'Macapá', 'AM': 'Manaus', 'BA': 'Salvador', 'CE': 'Fortaleza', 'DF': 'Brasília', 'ES': 'Vitória', 'GO': 'Goiânia', 'MA': 'São Luís', 'MT': 'Cuiabá', 'MS': 'Campo Grande', 'MG': 'Belo Horizonte', 'PA': 'Belém', 'PB': 'João Pessoa', 'PR': 'Curitiba', 'PE': 'Recife', 'PI': 'Teresina', 'RJ': 'Rio de Janeiro', 'RN': 'Natal', 'RS': 'Porto Alegre', 'RO': 'Porto Velho', 'RR': 'Boa Vista', 'SC': 'Florinópolis', 'SP': 'São Paulo', 'SE': 'Aracaju', 'TO': 'Palmas' }
    map_renda = { 'A': 'Nenhuma renda', 'B': 'Até 1 salário mínimo', 'C': 'De 1 a 1,5 salários mínimos', 'D': 'De 1,5 a 2 salários mínimos', 'E': 'De 2 a 2,5 salários mínimos', 'F': 'De 2,5 a 3 salários mínimos', 'G': 'De 3 a 4 salários mínimos', 'H': 'De 4 a 5 salários mínimos', 'I': 'De 5 a 6 salários mínimos', 'J': 'De 6 a 7 salários mínimos', 'K': 'De 7 a 8 salários mínimos', 'L': 'De 8 a 9 salários mínimos', 'M': 'De 9 a 10 salários mínimos', 'N': 'De 10 a 12 salários mínimos', 'O': 'De 12 a 15 salários mínimos', 'P': 'De 15 a 20 salários mínimos', 'Q': 'Mais de 20 salários mínimos' }
    map_escolaridade = { 'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5, 'F': 6, 'G': 7, 'H': 8 }
    map_escolaridade_reverso = { 1: 'Nunca estudou', 2: 'Não completou a 4ª série/5º ano', 3: 'Completou a 4ª série/5º ano', 4: 'Completou a 8ª série/9º ano', 5: 'Completou o Ensino Médio', 6: 'Completou a Faculdade', 7: 'Completou a Pós-graduação', 8: 'Não sabe' }
    map_faixa_etaria_adulto = { '1': 'Não', '2': 'Não', '3': 'Não', '4': 'Não', '5': 'Não', '6': 'Não', '7': 'Não', '8': 'Não', '9': 'Não', '10': 'Sim', '11': 'Sim', '12': 'Sim', '13': 'Sim', '14': 'Sim', '15': 'Sim', '16': 'Sim', '17': 'Sim', '18': 'Sim', '19': 'Sim', '20': 'Sim' }

    if 'SG_UF_PROVA' in df.columns: df['REGIAO_CANDIDATO'] = df['SG_UF_PROVA'].map(map_regiao)
    else: df['REGIAO_CANDIDATO'] = None
    if 'SG_UF_ESC' in df.columns: df['REGIAO_ESCOLA'] = df['SG_UF_ESC'].map(map_regiao)
    else: df['REGIAO_ESCOLA'] = None

    if 'SG_UF_PROVA' in df.columns and 'NO_MUNICIPIO_PROVA' in df.columns:
        capitais_da_uf_prova = df['SG_UF_PROVA'].map(map_capitais)
        is_capital_mask = (df['NO_MUNICIPIO_PROVA'] == capitais_da_uf_prova) & (df['NO_MUNICIPIO_PROVA'].notna())
        df['FLAG_CAPITAL'] = np.where(is_capital_mask, 'Sim', 'Não')
    else: df['FLAG_CAPITAL'] = 'Não'

    if 'TP_DEPENDENCIA_ADM_ESC' in df.columns:
        tp_dep_series = df['TP_DEPENDENCIA_ADM_ESC'].astype(str)
        df['TIPO_ESCOLA_AGRUPADO'] = None
        publica_mask = tp_dep_series.isin(['1', '2', '3'])
        privada_mask = tp_dep_series == '4'
        df.loc[publica_mask, 'TIPO_ESCOLA_AGRUPADO'] = 'Pública'
        df.loc[privada_mask, 'TIPO_ESCOLA_AGRUPADO'] = 'Privada'
    else: df['TIPO_ESCOLA_AGRUPADO'] = None

    cols_notas_objetivas = ['NU_NOTA_CN', 'NU_NOTA_CH', 'NU_NOTA_LC', 'NU_NOTA_MT']
    cols_notas_todas = cols_notas_objetivas + ['NU_NOTA_REDACAO']
    for col in cols_notas_todas:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')

    valid_obj_cols = [col for col in cols_notas_objetivas if col in df.columns and pd.api.types.is_numeric_dtype(df[col])]
    if len(valid_obj_cols) > 0: df['MEDIA_OBJETIVAS'] = df[valid_obj_cols].mean(axis=1).round(2)
    else: df['MEDIA_OBJETIVAS'] = np.nan
    valid_all_cols = [col for col in cols_notas_todas if col in df.columns and pd.api.types.is_numeric_dtype(df[col])]
    if len(valid_all_cols) > 0: df['MEDIA_GERAL'] = df[valid_all_cols].mean(axis=1).round(2)
    else: df['MEDIA_GERAL'] = np.nan

    presenca_cols_exist = [col for col in expected_presence_cols if col in df.columns]
    if presenca_cols_exist:
        df['INDICADOR_ABSENTEISMO'] = 'Presente'
        mask_abs = pd.Series(False, index=df.index); mask_elim = pd.Series(False, index=df.index)
        for col in presenca_cols_exist:
            presenca_series = df[col].astype(str)
            mask_abs |= (presenca_series == '0'); mask_elim |= (presenca_series == '2')
        df.loc[mask_abs, 'INDICADOR_ABSENTEISMO'] = 'Ausente em um ou mais dias'
        df.loc[mask_elim, 'INDICADOR_ABSENTEISMO'] = 'Eliminado'
    else: df['INDICADOR_ABSENTEISMO'] = 'N/A'

    if 'NU_NOTA_REDACAO' in df.columns and pd.api.types.is_numeric_dtype(df['NU_NOTA_REDACAO']):
        nota_red_series = df['NU_NOTA_REDACAO']
        df['INDICADOR_REDACAO_ZERADA'] = np.select([nota_red_series == 0, nota_red_series > 0], ['Sim', 'Não'], default='N/A')
    else: df['INDICADOR_REDACAO_ZERADA'] = 'N/A'

    if 'Q006' in df.columns: df['RENDA_FAMILIAR'] = df['Q006'].map(map_renda)
    else: df['RENDA_FAMILIAR'] = None

    if 'Q001' in df.columns and 'Q002' in df.columns:
        q001_num = df['Q001'].map(map_escolaridade).astype('Float64')
        q002_num = df['Q002'].map(map_escolaridade).astype('Float64') # Corrigido para Float64
        max_escolaridade_num = np.nanmax([q001_num, q002_num], axis=0)
        df['ESCOLARIDADE_PAIS_AGRUPADO'] = pd.Series(max_escolaridade_num, index=df.index).map(map_escolaridade_reverso)
        df['ESCOLARIDADE_PAIS_AGRUPADO'] = df['ESCOLARIDADE_PAIS_AGRUPADO'].fillna('Não informado')
    else: df['ESCOLARIDADE_PAIS_AGRUPADO'] = 'Não informado'

    if 'Q024' in df.columns and 'Q025' in df.columns:
        q024_series = df['Q024']; q025_series = df['Q025']
        conditions = [(q024_series == 'A') & (q025_series == 'A'), (q024_series != 'A') & (q025_series == 'A'), (q024_series == 'A') & (q025_series != 'A'), (q024_series != 'A') & (q025_series != 'A')]
        choices = ['Nenhum acesso', 'Apenas computador', 'Apenas internet', 'Acesso completo']
        df['INDICE_ACESSO_TECNOLOGIA'] = np.select(conditions, choices, default=None)
    else: df['INDICE_ACESSO_TECNOLOGIA'] = None

    if 'TP_ST_CONCLUSAO' in df.columns and 'NU_ANO' in df.columns and 'TP_ANO_CONCLUIU' in df.columns:
        df['TP_ANO_CONCLUIU'] = pd.to_numeric(df['TP_ANO_CONCLUIU'], errors='coerce')
        df['NU_ANO'] = pd.to_numeric(df['NU_ANO'], errors='coerce')
        st_concl_s = df['TP_ST_CONCLUSAO'].astype(str)
        tempo_fora = np.where((st_concl_s == '2') & df['NU_ANO'].notna() & df['TP_ANO_CONCLUIU'].notna() & (df['TP_ANO_CONCLUIU'] > 0), df['NU_ANO'] - df['TP_ANO_CONCLUIU'], None)
        df['TEMPO_FORA_ESCOLA'] = pd.Series(tempo_fora, index=df.index).astype('Int64')
    else: df['TEMPO_FORA_ESCOLA'] = pd.Series(index=df.index, dtype='Int64')

    if 'TP_FAIXA_ETARIA' in df.columns: df['FLAG_CANDIDATO_ADULTO'] = df['TP_FAIXA_ETARIA'].astype(str).map(map_faixa_etaria_adulto).fillna('Não')
    else: df['FLAG_CANDIDATO_ADULTO'] = 'Não'

    if 'NU_ANO' in df.columns: df['NU_ANO'] = pd.to_numeric(df['NU_ANO'], errors='coerce').astype('Int64')

    return df

# --- INÍCIO: FUNÇÕES DA FASE 4 ---

# --- FUNÇÃO 'criar_tabela_municipios_do_ibge' MODIFICADA (FASE 4A) ---
def criar_tabela_municipios_do_ibge(engine):
    """
    Carrega a tabela 'RELATORIO_MUNICIPIOS'
    a partir do arquivo local 'RELATORIO_DTB_BRASIL_2024_MUNICIPIOS.xls'.
    Lê apenas as 9 colunas especificadas para evitar colunas 'Unnamed'.
    """
    # NOME DA TABELA AJUSTADO
    nome_tabela_municipios_original = 'RELATORIO_MUNICIPIOS'
    
    # NOME DO ARQUIVO .XLS AJUSTADO
    nome_arquivo_xls = "RELATORIO_DTB_BRASIL_2024_MUNICIPIOS.xls"
    
    # Usa a variável global 'script_dir' definida no início do script
    caminho_arquivo_xls = os.path.join(script_dir, nome_arquivo_xls)
    
    # --- INÍCIO DA MODIFICAÇÃO (Correção UNNAMED_9) ---
    # Define explicitamente as 9 colunas que você renomeou no arquivo .XLS
    colunas_desejadas_municipios = [
        'UF', 'Nome_UF', 'REGIAO_GEOGRAFICA_INTERMEDIARIA', 
        'NOME_REGIAO_GEOGRAFICA_INTERMEDIARIA', 'REGIAO_GEOGRAFICA_IMEDIATA', 
        'NOME_REGIAO_GEOGRAFICA_IMEDIATA', 'MUNICIPIO', 'CO_MUNICIPIO', 'NOME_MUNICIPIO'
    ]
    # --- FIM DA MODIFICAÇÃO ---
    
    print(f"\n--- FASE 4A: Carga da Tabela de Municípios (Arquivo .XLS Local) ---")
    print(f"Lendo arquivo: {caminho_arquivo_xls}")
    print(f"Lendo APENAS as colunas: {colunas_desejadas_municipios}")

    try:
        try:
            # MÉTODO DE LEITURA AJUSTADO para pd.read_excel com engine 'xlrd'
            # ADICIONADO 'usecols' para ler apenas as colunas especificadas
            df_municipios = pd.read_excel(
                caminho_arquivo_xls, 
                engine='xlrd', 
                sheet_name=0, 
                usecols=colunas_desejadas_municipios
            )
            
        except FileNotFoundError:
            print(f"ERRO DE ARQUIVO: O arquivo '{nome_arquivo_xls}' não foi encontrado na pasta do script.")
            print(f"Caminho completo verificado: {caminho_arquivo_xls}")
            print("Por favor, adicione o arquivo a esta pasta e execute novamente.")
            return False
        except ImportError:
            print("ERRO DE IMPORTAÇÃO: A biblioteca 'xlrd' é necessária para ler arquivos .xls (Excel 97-2003).")
            print("Por favor, instale com: pip install xlrd")
            return False
        except ValueError as e_val:
            # Erro comum se os nomes das colunas no 'usecols' não baterem com o arquivo
            print(f"ERRO DE VALOR: Verifique se os nomes das colunas no script (usecols) batem EXATAMENTE com os nomes no arquivo XLS.")
            print(f"Detalhe: {e_val}")
            return False
        except Exception as e_xls:
            print(f"ERRO: Falha ao ler o arquivo Excel '{nome_arquivo_xls}'.")
            print(f"Erro detalhado: {e_xls}")
            return False

        if df_municipios.empty:
            print("Arquivo Excel lido, mas está vazio.")
            return False

        print(f"Dados lidos ({len(df_municipios)} linhas). Carregando para o banco...")

        # Limpa nomes das colunas para o SQL (remove acentos, espaços, etc.)
        # USA A FUNÇÃO NORMALIZE_COL_NAME QUE JÁ EXISTE NO SCRIPT
        df_municipios.columns = [
            re.sub(r'[^0-9a-zA-Z_]', '_', 
                   normalize_col_name(col).replace(' ', '_')
                  ) for col in df_municipios.columns
        ]
        
        # Conecta e sobe os dados
        with engine.connect() as connection:
            connection.execute(text(f'DROP TABLE IF EXISTS "{nome_tabela_municipios_original}" CASCADE;'))
            df_municipios.to_sql(
                nome_tabela_municipios_original,
                con=connection,
                if_exists='replace',
                index=False
            )
            connection.commit()
        
        print(f"Sucesso: Tabela '{nome_tabela_municipios_original}' criada no banco a partir do .xls.")
        return True # Retorna sucesso

    except Exception as e:
        print(f"ERRO na FASE 4A: Falha ao processar o arquivo .xls local. {e}")
        traceback.print_exc()
        return False # Retorna falha


def analisar_relacionamentos_municipios(engine, nome_tabela_microdados):
    """
    Analisa os relacionamentos entre a tabela 'RELATORIO_MUNICIPIOS'
    e a tabela de microdados.
    """
    # NOME DA TABELA ORIGINAL AJUSTADO
    nome_tabela_municipios = 'RELATORIO_MUNICIPIOS'
    
    print(f"\n--- FASE 4B: Análise de Relacionamentos ---")
    
    try:
        with engine.connect() as connection:
            # --- Tarefa 1: REMOVIDA (Não há mais cópia) ---

            # --- Tarefa 2: Verificar relacionamentos (colunas em comum) ---
            print("\nAnalisando possíveis relacionamentos...")
            
            # Pega os nomes das colunas de ambas as tabelas
            microdados_cols = pd.read_sql_query(text(f'SELECT * FROM "{nome_tabela_microdados}" LIMIT 1'), connection).columns
            # LÊ DA TABELA ORIGINAL, NÃO DA CÓPIA
            municipios_cols = pd.read_sql_query(text(f'SELECT * FROM "{nome_tabela_municipios}" LIMIT 1'), connection).columns
            
            # Normaliza (remove acentos e coloca em maiúsculo) para comparação
            set_microdados = set(normalize_col_name(col) for col in microdados_cols)
            set_municipios = set(normalize_col_name(col) for col in municipios_cols)
            
            # 1. Verificação de nomes EXATAMENTE IGUAIS
            colunas_comuns = set_microdados.intersection(set_municipios)
            
            if colunas_comuns:
                print("Relacionamento(s) por NOME EXATO encontrado(s)!\nColunas em comum (nomes normalizados):")
                for col in sorted(list(colunas_comuns)):
                    print(f"  - {col}")
            
            # 2. Verificação de NOMES LÓGICOS (A NOVA LÓGICA)
            print("\nVerificando relacionamentos lógicos (PK vs FK)...")

            # Define as colunas-chave da tabela de municípios (baseado no input do usuário)
            # O script normaliza "CO_MUNICIPIO", "NOME_MUNICIPIO", e "UF"
            chaves_municipios_esperadas = {'CO_MUNICIPIO', 'NOME_MUNICIPIO', 'UF'}
            
            # Define as chaves correspondentes na tabela de microdados (ENEM)
            mapa_relacionamentos = {
                'CO_MUNICIPIO': ['CO_MUNICIPIO_PROVA', 'CO_MUNICIPIO_ESC'],
                'NOME_MUNICIPIO': ['NO_MUNICIPIO_PROVA', 'NO_MUNICIPIO_ESC'],
                # Mapeia 'UF' (sigla) para as colunas de sigla e código da tabela de microdados
                'UF': ['SG_UF_PROVA', 'SG_UF_ESC', 'CO_UF_ESC', 'CO_UF_PROVA']
            }

            # Verifica se as colunas que esperamos existem na tabela de municípios
            chaves_municipios_encontradas = chaves_municipios_esperadas.intersection(set_municipios)
            
            if not chaves_municipios_encontradas:
                print(f"AVISO: Nenhuma das colunas-chave esperadas ({chaves_municipios_esperadas}) foi encontrada na tabela '{nome_tabela_municipios}'.")
                print(f"Colunas encontradas (normalizadas): {sorted(list(set_municipios))}")
                return

            print(f"Colunas-chave encontradas em '{nome_tabela_municipios}': {sorted(list(chaves_municipios_encontradas))}")
            
            relacionamentos_encontrados = False
            # Itera sobre as chaves que encontramos na tabela de municípios
            for chave_mun in chaves_municipios_encontradas:
                # Vê se essa chave tem correspondentes no mapa
                if chave_mun in mapa_relacionamentos:
                    # Pega as chaves equivalentes do ENEM (ex: ['CO_MUNICIPIO_PROVA', 'CO_MUNICIPIO_ESC'])
                    chaves_microdados_possiveis = mapa_relacionamentos[chave_mun]
                    
                    # Vê se alguma das chaves do ENEM existe na tabela de microdados
                    for chave_micro in chaves_microdados_possiveis:
                        if chave_micro in set_microdados:
                            print(f"  - Relacionamento Lógico Encontrado:")
                            print(f"     '{nome_tabela_municipios}'.{chave_mun}  ->  '{nome_tabela_microdados}'.{chave_micro}")
                            relacionamentos_encontrados = True

            if not relacionamentos_encontrados and not colunas_comuns:
                print("\nNenhum relacionamento lógico automático foi encontrado.")
                print(f"Colunas Microdados (normalizadas): {sorted(list(set_microdados))}")
                print(f"Colunas Municípios (normalizadas): {sorted(list(set_municipios))}")

    except Exception as e:
        print(f"\nERRO na FASE 4B ao tentar analisar a tabela.")
        print(f"Erro detalhado: {e}")

# --- FIM: FUNÇÕES DA FASE 4 ---


# --- INÍCIO: FUNÇÃO DA FASE 5 (AJUSTADA V5) ---

def criar_tabela_dicionario(engine):
    """
    Carrega a tabela 'dicionario_enem'
    a partir do arquivo local.
    Baseado na instrução do usuário (v5), procura por 'Dicionário.xlsx'
    e o lê como um arquivo Excel.
    A validação de colunas foi removida.
    """
    nome_tabela_dicionario = 'dicionario_enem'
    
    # --- NOME DO ARQUIVO AJUSTADO (conforme solicitação explícita do usuário) ---
    nome_arquivo_dicionario = "Dicionário.xlsx" 
    
    # Usa a variável global 'script_dir' definida no início do script
    caminho_arquivo = os.path.join(script_dir, nome_arquivo_dicionario)
    
    print(f"\n--- FASE 5: Carga da Tabela de Dicionário ---")
    print(f"Lendo arquivo: {caminho_arquivo}")

    df_dicionario = None
    
    try:
        try:
            # --- LÓGICA DE LEITURA AJUSTADA ---
            # Tenta ler diretamente como Excel (requer 'openpyxl')
            print(" 1. Tentando ler como arquivo Excel (Dicionário.xlsx)...")
            df_dicionario = pd.read_excel(caminho_arquivo, sheet_name=0)
            print("    ... Sucesso (lido como Excel).")
        
        except FileNotFoundError:
            # Lança a exceção para ser capturada pelo 'except FileNotFoundError' externo
            raise FileNotFoundError
        
        except Exception as e_excel:
            print(f"    ... Falha ao ler como Excel: {e_excel}")
            # Adiciona verificação de biblioteca (openpyxl para .xlsx)
            if "support for the file format" in str(e_excel) or "'openpyxl'" in str(e_excel):
                print("    AVISO: Verifique se a biblioteca correta para ler .xlsx está instalada.")
                print("    Execute: pip install openpyxl")
            # Lança a exceção para ser capturada pelo 'except Exception as e' externo
            raise e_excel 
        
        # --- FIM DA LÓGICA DE LEITURA ---

        if df_dicionario is None or df_dicionario.empty:
            print("Arquivo do dicionário lido, mas está vazio.")
            return False

        print(f"Dados lidos ({len(df_dicionario)} linhas). Carregando para o banco...")

        # Normaliza os nomes das colunas (ex: 'questao' -> 'QUESTAO')
        df_dicionario.columns = [normalize_col_name(col) for col in df_dicionario.columns]
        
        # --- BLOCO DE VALIDAÇÃO DE COLUNAS REMOVIDO (conforme solicitação) ---
        # O script não vai mais checar por 'QUESTAO', 'RESPOSTA', 'DESCRICAO'
        print(f"Colunas encontradas e normalizadas: {list(df_dicionario.columns)}")
        # --- FIM DA REMOÇÃO ---

        # Conecta e sobe os dados
        with engine.connect() as connection:
            connection.execute(text(f'DROP TABLE IF EXISTS "{nome_tabela_dicionario}" CASCADE;'))
            df_dicionario.to_sql(
                nome_tabela_dicionario,
                con=connection,
                if_exists='replace',
                index=False
            )
            connection.commit()
        
        print(f"Sucesso: Tabela '{nome_tabela_dicionario}' criada no banco a partir do arquivo.")
        return True # Retorna sucesso

    except FileNotFoundError: # Captura a FileNotFoundError de pd.read_excel
        print(f"ERRO DE ARQUIVO: O arquivo '{nome_arquivo_dicionario}' não foi encontrado na pasta do script.")
        print(f"Caminho completo verificado: {caminho_arquivo}")
        return False
    except Exception as e:
        print(f"ERRO na FASE 5: Falha ao processar o arquivo do dicionário. {e}")
        traceback.print_exc()
        return False # Retorna falha

# --- FIM: FUNÇÃO DA FASE 5 (AJUSTADA V5) ---


# --- SCRIPT PRINCIPAL ---
if __name__ == "__main__":
    start_time_total = time.time()
    
    # Adicionado pool_pre_ping=True para verificar conexões antes de usar
    engine = create_engine(
        DATABASE_URL, 
        pool_size=10, 
        max_overflow=15, 
        pool_timeout=60, 
        pool_pre_ping=True 
    )
    
    # Busca arquivos CSV de microdados
    arquivos_csv = glob.glob(os.path.join(diretorio_csv, '*.csv'))
    
    # Filtra para NÃO incluir o CSV de campos calculados
    # E TAMBÉM NÃO incluir o CSV do Dicionário
    # (O Dicionário agora é .xlsx, então este filtro não o afetaria,
    # mas mantemos a exclusão explícita por segurança)
    arquivos_csv = [f for f in arquivos_csv if 'Campos Calculados' not in f and 'Dicionário' not in f]


    if not arquivos_csv: 
        print(f"AVISO: Nenhum arquivo .csv de microdados (ENEM/PARTICIPANTES) encontrado em: {diretorio_csv}")
        # Não usamos exit() para permitir que a FASE 4 e 5 rodem mesmo assim
    else:
        print("--- FASE 1: Analisando cabeçalhos... ---")
        master_columns = set(campos_desejados); all_file_headers = {}
        for arquivo in arquivos_csv:
            try:
                filename = os.path.basename(arquivo); print(f"Lendo: {filename}")
                raw_header = pd.read_csv(arquivo, encoding='latin1', sep=';', nrows=0, low_memory=False).columns
                header = [normalize_col_name(h) for h in raw_header]
                all_file_headers[filename] = header; master_columns.update(header)
            except Exception as e: print(f" Aviso: Falha ao ler {filename}. Erro: {e}"); all_file_headers[filename] = []
        if 'NU_SEQUENCIAL' in master_columns: master_columns.remove('NU_SEQUENCIAL'); master_columns.add('NU_INSCRICAO'); print(" Coluna 'NU_SEQUENCIAL' mapeada para 'NU_INSCRICAO'.")
        extra_qs = [col for col in master_columns if col.startswith('Q') and len(col) > 1 and col[1:].isdigit() and int(col[1:]) > 25]
        if extra_qs: print(f" Removendo Q>25: {extra_qs}"); master_columns -= set(extra_qs)
        novos_campos = [ 'REGIAO_CANDIDATO', 'FLAG_CAPITAL', 'REGIAO_ESCOLA', 'TIPO_ESCOLA_AGRUPADO', 'MEDIA_OBJETIVAS', 'MEDIA_GERAL', 'INDICADOR_ABSENTEISMO', 'INDICADOR_REDACAO_ZERADA', 'RENDA_FAMILIAR', 'ESCOLARIDADE_PAIS_AGRUPADO', 'INDICE_ACESSO_TECNOLOGIA', 'TEMPO_FORA_ESCOLA', 'FLAG_CANDIDATO_ADULTO' ]
        master_columns.update(novos_campos); master_columns_list = sorted(list(master_columns))
        print(f"\nColunas finais ({len(master_columns_list)}): {master_columns_list}")

        tipos_de_dados_sql = {}
        for col in master_columns_list:
            if col in ['NU_NOTA_CN', 'NU_NOTA_CH', 'NU_NOTA_LC', 'NU_NOTA_MT', 'NU_NOTA_COMP1', 'NU_NOTA_COMP2', 'NU_NOTA_COMP3', 'NU_NOTA_COMP4', 'NU_NOTA_COMP5', 'NU_NOTA_REDACAO', 'MEDIA_OBJETIVAS', 'MEDIA_GERAL']: tipos_de_dados_sql[col] = types.NUMERIC(10, 2)
            elif col in ['NU_ANO', 'TEMPO_FORA_ESCOLA']: tipos_de_dados_sql[col] = types.INTEGER
            elif col in ['NU_INSCRICAO']: tipos_de_dados_sql[col] = types.BIGINT
            elif col.startswith('CO_') or col in ['TP_FAIXA_ETARIA', 'TP_COR_RACA', 'TP_NACIONALIDADE', 'TP_ST_CONCLUSAO', 'TP_ANO_CONCLUIU', 'TP_ESCOLA', 'TP_ENSINO', 'IN_TREINEIRO', 'TP_DEPENDENCIA_ADM_ESC', 'TP_LOCALIZACAO_ESC', 'TP_SIT_FUNC_ESC', 'TP_PRESENCA_CN', 'TP_PRESENCA_CH', 'TP_PRESENCA_LC', 'TP_PRESENCA_MT', 'TP_LINGUA', 'TP_STATUS_REDACAO', 'Q005', 'TP_ESTADO_CIVIL']: # Adicionado TP_ESTADO_CIVIL
                 tipos_de_dados_sql[col] = types.INTEGER # Mantendo INTEGER para códigos e tipos
            else: tipos_de_dados_sql[col] = types.VARCHAR
        print(f"\nTipos SQL definidos: {tipos_de_dados_sql}")

        print("\n--- FASE 2: Processando e carregando arquivos ---")
        is_first_upload = True; total_rows_processed = 0
        try:
            with engine.connect() as connection: connection.execute(text(f'DROP TABLE IF EXISTS "{nome_tabela}" CASCADE;')); connection.commit()
            print(f"Tabela '{nome_tabela}' antiga removida.")
        except Exception as e: print(f"Aviso: Falha ao dropar tabela. Erro: {e}")
        try:
            empty_df = pd.DataFrame(columns=master_columns_list).astype({col: 'float64' for col, dtype in tipos_de_dados_sql.items() if isinstance(dtype, (types.NUMERIC, types.FLOAT))} | {col: 'Int64' for col, dtype in tipos_de_dados_sql.items() if isinstance(dtype, (types.INTEGER, types.BIGINT))} | {col: 'object' for col, dtype in tipos_de_dados_sql.items() if isinstance(dtype, (types.VARCHAR, types.TEXT))})
            print("Criando schema da tabela no banco..."); empty_df.to_sql( name=nome_tabela, con=engine, if_exists='replace', index=False, dtype=tipos_de_dados_sql ); print("Schema criado.")
            is_first_upload = False
        except Exception as e: print(f"\nERRO CRÍTICO ao criar schema '{nome_tabela}'. Abortando.\nErro: {e}"); traceback.print_exc(); engine.dispose(); exit()

        for arquivo in arquivos_csv:
            start_time_file = time.time(); filename = os.path.basename(arquivo); print(f"\nProcessando: {filename}")
            try:
                match = re.search(r'(19|20)\d{2}', filename)
                if match: ano_arquivo = int(match.group(0))
                else: raise ValueError("Ano não encontrado")
                print(f"  Ano: {ano_arquivo}")
            except ValueError as e: print(f"  Aviso: {e} em '{filename}'. Pulando."); continue

            rows_in_file = 0
            try:
                file_specific_header_normalized = all_file_headers.get(filename, [])
                if not file_specific_header_normalized:
                        print(f"  Aviso: Cabeçalho não lido na Fase 1 para {filename}. Lendo novamente.")
                        raw_header = pd.read_csv(arquivo, encoding='latin1', sep=';', nrows=0, low_memory=False).columns
                        file_specific_header_normalized = [normalize_col_name(h) for h in raw_header]
                usecols_normalized = [col for col in file_specific_header_normalized if col in master_columns_list]
                try: # Tenta mapear de volta, pode falhar se o cabeçalho mudou ou teve erro na Fase 1
                    raw_header_map = {normalize_col_name(h): h for h in pd.read_csv(arquivo, encoding='latin1', sep=';', nrows=0, low_memory=False).columns}
                    usecols_original = [raw_header_map[norm_col] for norm_col in usecols_normalized if norm_col in raw_header_map]
                    if not usecols_original: # Se mapeamento falhar, lê todas as colunas como fallback
                        print("   Aviso: Mapeamento de colunas falhou, lendo todas as colunas.")
                        usecols_original = None
                except Exception as map_err:
                        print(f"   Aviso: Erro ao mapear colunas para leitura otimizada ({map_err}), lendo todas as colunas.")
                        usecols_original = None

                reader = pd.read_csv( arquivo, encoding='latin1', sep=';', chunksize=chunk_size, low_memory=False, usecols=usecols_original )
                for i, chunk in enumerate(reader):
                    start_time_chunk = time.time()
                    try:
                        chunk.columns = [normalize_col_name(c) for c in chunk.columns]
                        if 'NU_SEQUENCIAL' in chunk.columns: chunk.rename(columns={'NU_SEQUENCIAL': 'NU_INSCRICAO'}, inplace=True)
                        
                        # Aplica regras de negócio (usando cópia para segurança)
                        # Seleciona colunas *antes* de passar para a função
                        cols_present_in_chunk = [col for col in master_columns_list if col in chunk.columns]
                        chunk_processado = aplicar_regras_de_negocio(chunk[cols_present_in_chunk].copy(), ano_arquivo)
                        
                        # Reindexa para o schema mestre
                        chunk_alinhado = chunk_processado.reindex(columns=master_columns_list)

                        # --- INÍCIO DA LÓGICA DE COERÇÃO REFINADA ---
                        for col, sql_type in tipos_de_dados_sql.items():
                                if col in chunk_alinhado.columns:
                                    try:
                                        # Trata tipos numéricos (NUMERIC, FLOAT, INTEGER, BIGINT)
                                        if isinstance(sql_type, (types.NUMERIC, types.FLOAT, types.INTEGER, types.BIGINT)):
                                            # 1. Substitui strings vazias por NaN ANTES de coagir
                                            chunk_alinhado.loc[chunk_alinhado[col] == '', col] = np.nan
                                            
                                            # 2. Coage para numérico, transformando outros erros em NaN
                                            numeric_series = pd.to_numeric(chunk_alinhado[col], errors='coerce')

                                            # 3. Atribui de volta baseado no tipo SQL específico
                                            if isinstance(sql_type, (types.INTEGER, types.BIGINT)):
                                                chunk_alinhado[col] = numeric_series.astype('Int64') # Usa Int64 que suporta nulos (NaN)
                                            else: # NUMERIC, FLOAT
                                                chunk_alinhado[col] = numeric_series # Deixa como float64
                                        
                                        # Trata tipos string (VARCHAR, TEXT)
                                        elif isinstance(sql_type, (types.VARCHAR, types.TEXT)):
                                            # Converte para string, substitui nulos/vazios por None
                                            chunk_alinhado[col] = chunk_alinhado[col].astype(str).replace('<NA>', None).replace('nan', None).replace('', None)

                                        # Adicione outros tipos se necessário
                                        # else: pass

                                    except Exception as coerc_e:
                                        print(f"\n   Alerta de Coerção inesperado na coluna '{col}': {coerc_e}. Forçando None.")
                                        chunk_alinhado[col] = None
                        # --- FIM DA LÓGICA DE COERÇÃO REFINADA ---

                        print(f"  Chunk {i+1}: {len(chunk_alinhado)} linhas. Processando e convertendo tipos...", end="", flush=True)

                        chunk_alinhado.to_sql( name=nome_tabela, con=engine, if_exists='append', index=False, method='multi', chunksize=upload_chunksize )
                        end_time_chunk = time.time(); rows_in_file += len(chunk_alinhado); total_rows_processed += len(chunk_alinhado)
                        print(f" OK. ({end_time_chunk - start_time_chunk:.2f}s)")
                    except Exception as e_chunk: print(f"\n  Falha no chunk {i+1} de {filename}: {str(e_chunk)}"); traceback.print_exc(); print(f"  Pulando chunk {i+1}.")
                
                # --- ESTA É A LINHA CORRIGIDA ---
                # Ela foi movida para dentro do bloco 'try' (indentada)
                end_time_file = time.time(); print(f"  Arquivo {filename} ({rows_in_file} linhas) processado em {end_time_file - start_time_file:.2f}s.")
            
            except Exception as e_file: print(f"\n  Falha ao processar {filename}: {str(e_file)}"); traceback.print_exc(); print(f"  Pulando {filename}.")

        end_time_total = time.time(); print(f"\nProcessamento concluído em {end_time_total - start_time_total:.2f}s.")
        print(f"Total de {total_rows_processed} linhas inseridas em '{nome_tabela}'.")

    # --- INÍCIO DA SEÇÃO MODIFICADA (FASE 3 e 4) ---

    print("\n--- FASE 3: Verificando dados no banco... ---")
    
    # Verifica a tabela de microdados apenas se ela foi processada
    if arquivos_csv: 
        try:
            with engine.connect() as connection:
                total_db_rows = connection.execute(text(f'SELECT COUNT(*) FROM "{nome_tabela}";')).scalar_one()
                if total_db_rows > 0:
                        print(f"Contagem total na tabela '{nome_tabela}': {total_db_rows}")
                        df_verificacao = pd.read_sql_query(text(f'SELECT "NU_ANO", COUNT(*) as total_registros FROM "{nome_tabela}" GROUP BY "NU_ANO" ORDER BY "NU_ANO";'), connection)
                        print("Contagem por ano:"); print(df_verificacao.to_string(index=False))
                else: 
                        print(f"Tabela '{nome_tabela}' criada, mas vazia (0 registros). Verifique logs.")
        except Exception as e: 
            print(f"Erro ao verificar dados da tabela '{nome_tabela}': {e}")
    else:
        print("Pula verificação da FASE 3 (nenhum microdado processado).")


    print("\n--- FASE 4: Carga e Análise da Tabela de Municípios ---")
    
    # 4A: Tenta carregar a tabela principal do IBGE a partir do .XLS local
    # Esta função irá criar 'RELATORIO_MUNICIPIOS'
    sucesso_carga_ibge = criar_tabela_municipios_do_ibge(engine)
    
    # 4B: Se a tabela foi criada E a tabela de microdados também existe, executa a análise
    if sucesso_carga_ibge and arquivos_csv:
        # Esta função (MODIFICADA) agora apenas analisa
        # a relação com 'dados_enem_consolidado' (a var 'nome_tabela')
        analisar_relacionamentos_municipios(engine, nome_tabela)
    elif not sucesso_carga_ibge:
        print("\n--- FASE 4B: Pula Análise de Relacionamentos (Carga da DTB falhou) ---")
    elif not arquivos_csv:
         print(f"\n--- FASE 4B: Pula Análise de Relacionamentos (Tabela '{nome_tabela}' não foi carregada) ---")
    
    # --- FIM DA NOVA LÓGICA ADICIONADA ---

    # --- INÍCIO DA ADIÇÃO (FASE 5) ---
    # Tenta carregar a tabela de dicionário
    criar_tabela_dicionario(engine)
    # --- FIM DA ADIÇÃO (FASE 5) ---

    engine.dispose(); print("Pool de conexões liberado.")

    # --- FIM DA SEÇÃO MODIFICADA ---