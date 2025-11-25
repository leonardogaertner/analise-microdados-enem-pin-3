# Processador e Consolidador de Microdados do ENEM

## Descrição

Este script é uma ferramenta de ETL (Extração, Transformação e Carga) projetada para processar múltiplos arquivos de microdados do ENEM em formato `.csv`. Ele limpa, transforma e consolida os dados de vários anos em uma única tabela em um banco de dados PostgreSQL, preparando-os para análise.

## Funcionalidades Principais

- **Consolidação de Múltiplos Anos:** Encontra e processa automaticamente todos os arquivos `.csv` de microdados no diretório.
- **Processamento Eficiente de Memória:** Lê e processa arquivos grandes em "pedaços" (chunks), permitindo a execução em computadores com memória limitada.
- **Limpeza e Padronização de Dados:** Converte tipos de dados, remove espaços em branco e unifica o esquema de colunas entre diferentes anos.
- **Lógica de Negócio Customizada:** Aplica regras de negócio específicas para corrigir inconsistências e mapear dados entre diferentes layouts de anos.
- **Carga Otimizada:** Utiliza o comando `COPY` do PostgreSQL para uma inserção de dados em massa de alta performance.
- **Verificação Pós-Carga:** Ao final da execução, realiza uma contagem de registros por ano diretamente no banco de dados para confirmar o sucesso da operação.

## Pré-requisitos

Certifique-se de que você tem o Python instalado, assim como as seguintes bibliotecas. Você pode instalá-las com o pip:

```bash
pip install pandas sqlalchemy numpy psycopg2-binary
```

## Configuração

1.  **Arquivos CSV:** Coloque todos os seus arquivos de microdados do ENEM (ex: `MICRODADOS_ENEM_2014_5k.csv`) na mesma pasta que o `script.py`.
2.  **Banco de Dados:** Edite as seguintes linhas no topo do `script.py` com as suas credenciais de acesso ao PostgreSQL:

    ```python
    DB_USER = 'postgres'
    DB_PASS = 'aluno'
    DB_HOST = 'localhost'
    DB_NAME = 'microdados'
    ```

## Como Executar

1.  Abra um terminal, navegue até a pasta do projeto e execute o script de carga:
    ```bash
    python script.py
    ```
2.  Após a conclusão, execute o script SQL (detalhado abaixo) no seu cliente de banco de dados para calcular os valores de `IN_TREINEIRO` para 2014.

## Lógica de Transformação Detalhada

### Regras Gerais de Limpeza

- **Esquema Unificado:** O script primeiro lê o cabeçalho de todos os arquivos para criar uma lista mestra de colunas. Ao processar cada arquivo, ele garante que os dados se alinhem a esse esquema, preenchendo colunas ausentes com `NULO`.
- **Conversão para Inteiro:** Colunas que representam códigos ou tipos (nomes que começam com `CO_`, `TP_`, `NU_ANO`, `IN_`) são limpas de espaços em branco e convertidas para um tipo numérico inteiro.
    - **Exceção:** A coluna `TP_SEXO` é tratada corretamente como texto.
- **Caso Especial 2024:** O arquivo `RESULTADOS_2024.csv` é intencionalmente ignorado, utilizando-se apenas o `PARTICIPANTES_2024.csv` para este ano.

### Regras de Negócio Específicas por Ano

#### Ano de 2024
- A coluna `Q006` recebe o valor de `Q007`, e em seguida a coluna `Q007` é definida como `NULO`.
- A coluna `Q024` recebe o valor de `Q021`, e em seguida a coluna `Q021` é definida como `NULO`.
- **Campos 2024 Nulos:** Algumas colunas da tabela de 2024 ficaram como null no banco de dados, pois os dados foram colocados em duas planilhas diferentes: `RESULTADOS_2024` e `PARTICIPANTES_2024`. No entanto, não haviam chaves extrangeiras entre as tabelas, impossibilitando a referência dos registros.

#### Ano de 2014
- **Cópia e Mapeamento:**
    - `Q005` recebe o valor de `Q004`.
    - `Q006` recebe o valor de `Q003`.
    - O valor de `Q010` é mapeado e salvo em `Q024`.
    - O valor de `Q015` é mapeado e salvo em `Q023`.
    - O valor de `Q016` é mapeado e salvo em `Q022`.
    - O valor de `Q017` é mapeado e salvo em `Q025`.
- **Anulação de Colunas de Origem:** Para evitar duplicação, todas as colunas de origem de 2014 (`Q003`, `Q004`, `Q007`, `Q010`, `Q015`, `Q016`, `Q017`) são definidas como `NULO` após suas transformações.
- **Mapeamento de Valores (aplicado nas regras acima):**
    - `A` vira `B`
    - `B` vira `C`
    - `C` vira `NULO`
    - `D` vira `A`

## Passo Pós-Carga Manual: Cálculo do IN_TREINEIRO (2014)

Devido a inconsistências persistentes, o cálculo de `IN_TREINEIRO` para 2014 foi removido do script Python. Execute o seguinte comando SQL **após** o script Python terminar a carga dos dados.

1.  **Script de Atualização (UPDATE):**
    ```sql
    UPDATE public.dados_enem_consolidado
    SET "IN_TREINEIRO" = CASE
        WHEN "TP_ST_CONCLUSAO" = 3 AND "TP_FAIXA_ETARIA" <= 2 THEN 1
        ELSE 0
    END
    WHERE "NU_ANO" = 2014;
    ```

2.  **Script de Verificação (SELECT):**
    ```sql
    SELECT
        "IN_TREINEIRO",
        COUNT(*) as total_registros
    FROM
        public.dados_enem_consolidado
    WHERE
        "NU_ANO" = 2014
    GROUP BY
        "IN_TREINEIRO";
    ```